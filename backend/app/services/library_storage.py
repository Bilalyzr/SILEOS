"""Private ebook file storage (spec §3 — the crux: paid content must not leak).

Files live under backend/ebooks/{owner_id}/{uuid}.{ext} — NOT under
uploads/, which nginx serves publicly. Serving happens exclusively through
the authenticated /download and the app-streamed /sample endpoints in
app/routers/library.py (mirrors the company-invoicing private-PDF pattern:
FileResponse, never a static redirect).

Hardening (reuses core/secure_upload.py's posture where applicable, and
mirrors h5p_service.py's hardened-zip posture for the EPUB path):
  - extension allowlist {pdf, epub}; the CLIENT filename is used ONLY for an
    early allowlist pre-check (fast rejection of obviously-wrong uploads) —
    it never determines the stored extension. The bytes are sniffed AFTER
    they land on disk and the SNIFF RESULT decides the final extension.
  - magic-byte sniff: PDF must start "%PDF-" (prefix-only check — see the
    M1 note below); EPUB must be a real, unencrypted zip (PK\x03\x04) that
    passes the OCF `mimetype`-entry contract exactly (see _sniff_epub).
  - zip-bomb / decompression-bomb guards on the EPUB path, mirroring
    h5p_service.py exactly (MAX_EPUB_ENTRIES=2000, MAX_EPUB_UNCOMPRESSED=
    300MiB): a declared-entry-count cap and a declared-uncompressed-size
    cap are enforced from the central directory BEFORE any entry is read,
    and the `mimetype` entry itself is read via a bounded stream (never
    zf.read(name), which materializes the whole entry). A SECOND,
    independent compression-ratio guard (MAX_EPUB_RATIO=100, applied only
    once the declared total clears MAX_EPUB_RATIO_FLOOR=10MiB) rejects a
    declared size that is implausible relative to the archive's actual
    on-disk (compressed) size — an absolute cap alone still let a
    near-empty zip declare 200MB, comfortably under 300MiB yet still a
    bomb.
  - encrypted zips (flag_bits & 0x1) are rejected as a clean 400 — zipfile
    raises RuntimeError/NotImplementedError deep inside read()/open() for
    these, so callers must never let those escape uncaught.
  - 200MB per-file cap enforced WHILE streaming (a liar Content-Length
    can't help); 5GB per-owner cap measured from actual DB rows
    (ebooks.file_size_bytes for the owner), NOT an on-disk walk — a walk
    can be inflated by orphan files that were never charged against the
    owner's real library contents. `db` is a REQUIRED argument to
    save_ebook_file specifically so this check can never be silently
    skipped by a caller forgetting to pass a session (fail-closed, not
    fail-open).
  - abandoned .part temp files (a request that died mid-stream before
    cleanup ran) are reaped at the start of every save so they can never
    accumulate or be counted against anything.
  - normalize-and-reassert: every path is resolved and asserted inside
    EBOOKS_ROOT both before writing and before serving.
  - failed validation leaves no bytes behind (.part temp is unlinked).
  - EBOOKS_ROOT is an absolute path anchored to the backend package
    directory (overridable via the EBOOKS_DIR env var) — NOT a bare
    Path("ebooks"), which would be silently CWD-relative and break under
    any process manager that runs the app from a different working
    directory (mirrors how invoice_pdf.py's INVOICES_DIR is handled, fixed
    to be cwd-independent).

Accepted-risk notes (adversarial review rulings, kept here so the
reasoning travels with the code):
  - M1: the PDF sniff is prefix-only ("%PDF-"). A full PDF parser is out of
    scope for this service; a file that merely starts with the PDF magic
    bytes but is otherwise malformed is a corrupt-file problem for the PDF
    reader, not a security boundary this module is responsible for.
  - TOCTOU on the owner cap (two concurrent uploads can both pass the
    pre-write DB check and jointly exceed MAX_OWNER_TOTAL_BYTES before
    either commits): accepted. Only approved instructors can reach this
    path and the overshoot is bounded by at most one extra MAX_FILE_BYTES-
    sized file — not worth serializing uploads over.
  - Write-then-validate ordering (bytes hit a .part file before the sniff
    runs) is accepted as long as the sniff/caps all run before the final
    rename to the served filename, and the .part cleanup-on-failure
    contract stays intact — both remain true here.

Callers import the MODULE (`from app.services import library_storage`) and
use attribute access so tests can monkeypatch EBOOKS_ROOT and the caps.
"""
import logging
import os
import time
import uuid
from pathlib import Path
from zipfile import BadZipFile, ZipFile

from fastapi import HTTPException, UploadFile, status

logger = logging.getLogger(__name__)

# Anchored to the backend package directory (backend/app/services/../../ ==
# backend/), NOT the process cwd — Path("ebooks") alone would resolve
# relative to whatever directory the app happens to be launched from
# (uvicorn's --reload, a supervisord `directory=`, a test runner, etc. can
# all differ), silently scattering files across hosts/deploys. EBOOKS_DIR
# lets ops override this (e.g. to point at a mounted volume) the same way
# other path-like settings in this codebase are overridden via env vars.
_BACKEND_DIR = Path(__file__).resolve().parents[2]
EBOOKS_ROOT = Path(os.environ.get("EBOOKS_DIR") or (_BACKEND_DIR / "ebooks"))
if not EBOOKS_ROOT.is_absolute():
    EBOOKS_ROOT = (_BACKEND_DIR / EBOOKS_ROOT).resolve()

ALLOWED_EXTENSIONS = {"pdf", "epub"}
MAX_FILE_BYTES = 200 * 1024 * 1024              # 200MB per file (spec §3)
MAX_OWNER_TOTAL_BYTES = 5 * 1024 * 1024 * 1024  # 5GB per owner (spec §3)
_CHUNK = 1024 * 1024

# EPUB zip-bomb guards (mirrors h5p_service.py's posture exactly: 300MiB /
# 2000 entries — declared-metadata caps checked before any read). Round 3
# lowered these from an earlier 1 GiB / 5000 after the re-review showed a
# ~1MB payload declaring ~1GiB (1029x ratio) was accepted under the looser
# cap. MAX_EPUB_RATIO is a second, independent guard: even a declared size
# UNDER the absolute cap can still be a bomb relative to how little data
# was actually shipped (e.g. a near-empty zip declaring 200MB) — reject
# when declared_total > MAX_EPUB_RATIO x compressed_size on disk. The ratio
# check only applies once declared_total exceeds MAX_EPUB_RATIO_FLOOR, so a
# legitimately tiny epub (a few KB of real content compressing extremely
# well) is never penalized for a high ratio that doesn't matter in absolute
# terms.
MAX_EPUB_ENTRIES = 2000
MAX_EPUB_UNCOMPRESSED = 300 * 1024 * 1024  # 300 MiB total declared
MAX_EPUB_RATIO = 100
MAX_EPUB_RATIO_FLOOR = 10 * 1024 * 1024  # 10 MiB — below this, ratio is ignored

# Stale .part files (a request that died mid-upload) older than this are
# swept at the start of every save (I1).
_DEFAULT_STALE_PART_SECONDS = 3600

MEDIA_TYPES = {
    "pdf": "application/pdf",
    "epub": "application/epub+zip",
}

_GENERIC_UPLOAD_ERROR = "Uploaded file failed validation"


def _owner_dir(owner_id: int) -> Path:
    return EBOOKS_ROOT / str(int(owner_id))


def owner_total_bytes(db, owner_id: int) -> int:
    """Sum of Ebook.file_size_bytes for everything this owner has on
    record — the DB is the source of truth for the per-owner cap (I1), not
    a walk of the owner's on-disk directory (which an orphan/replaced file
    could inflate without ever having been charged against the owner)."""
    from app.models.ebook import Ebook

    total = (
        db.query(Ebook)
        .filter(Ebook.owner_id == int(owner_id))
        .with_entities(Ebook.file_size_bytes)
        .all()
    )
    return sum((row[0] or 0) for row in total)


def reap_stale_parts(owner_dir: Path, older_than_seconds: int = _DEFAULT_STALE_PART_SECONDS) -> None:
    """Delete abandoned `.part` temp files under `owner_dir` older than
    `older_than_seconds` (a request that died mid-stream before the
    finally-block cleanup ran). Never raises — best-effort housekeeping."""
    owner_dir = Path(owner_dir)
    if not owner_dir.exists():
        return
    cutoff = time.time() - older_than_seconds
    try:
        for p in owner_dir.glob("*.part"):
            try:
                if p.is_file() and p.stat().st_mtime < cutoff:
                    p.unlink(missing_ok=True)
            except OSError:
                logger.warning("could not reap stale part file %s", p)
    except OSError:
        logger.warning("could not scan %s for stale part files", owner_dir)


def _reject(detail: str, status_code: int = status.HTTP_400_BAD_REQUEST) -> None:
    raise HTTPException(status_code=status_code, detail=detail)


def _sniff_pdf(path: Path) -> bool:
    """M1 (accepted): prefix-only sniff. See module docstring."""
    with open(path, "rb") as f:
        return f.read(5) == b"%PDF-"


def _sniff_epub(path: Path) -> bool:
    """Full OCF-conformant EPUB sniff, hardened against zip bombs and
    encrypted archives (C1, C2, I2). Returns True/False; never raises for
    "this just isn't a valid epub" — callers turn a False into a clean 400.
    Raises HTTPException directly for the cap violations so the specific
    reason (entry count / size) is preserved in the response.
    """
    with open(path, "rb") as f:
        if f.read(4) != b"PK\x03\x04":
            return False

    try:
        zf = ZipFile(path)
    except BadZipFile:
        return False

    with zf:
        try:
            infolist = zf.infolist()
        except BadZipFile:
            return False

        # ---- C2: declared-metadata caps BEFORE any entry is read. ----
        if len(infolist) > MAX_EPUB_ENTRIES:
            _reject(f"EPUB contains too many entries ({len(infolist)} > {MAX_EPUB_ENTRIES})")

        total_declared = 0
        for info in infolist:
            total_declared += info.file_size
            if total_declared > MAX_EPUB_UNCOMPRESSED:
                _reject(
                    "EPUB's declared uncompressed size exceeds the "
                    f"{MAX_EPUB_UNCOMPRESSED} byte limit"
                )

        # ---- New-1 (Round 3): compression-ratio guard, independent of the
        # absolute cap above. A declared total can sit comfortably under
        # MAX_EPUB_UNCOMPRESSED yet still be a bomb relative to how little
        # data the archive actually carries on disk (e.g. a near-empty zip
        # declaring 200MB for one entry). Compare against the ACTUAL
        # on-disk archive size (the compressed bytes the uploader really
        # sent), never a declared/compressed-size field from the zip
        # metadata itself, which is just as attacker-controlled as
        # file_size. Only applied once the declared total clears
        # MAX_EPUB_RATIO_FLOOR — a small legitimate epub that happens to
        # compress very well must never be penalized. ----
        if total_declared > MAX_EPUB_RATIO_FLOOR:
            compressed_size = Path(path).stat().st_size
            if compressed_size == 0 or total_declared > MAX_EPUB_RATIO * compressed_size:
                _reject(
                    "EPUB's declared uncompressed size is implausible relative "
                    "to its actual size on disk (possible decompression bomb)"
                )

        # ---- C1: reject any encrypted entry cleanly, never let zipfile's
        # RuntimeError/NotImplementedError escape uncaught. ----
        for info in infolist:
            if info.flag_bits & 0x1:
                _reject("EPUB contains an encrypted archive entry")

        if not infolist:
            return False

        # ---- I2: strict OCF mimetype contract — first entry, stored
        # (uncompressed), exact bytes, no whitespace tolerance. ----
        first = infolist[0]
        if first.filename != "mimetype":
            return False
        if first.compress_type != 0:  # ZIP_STORED
            return False

        # Bounded read of the mimetype entry only — never zf.read(name),
        # which would materialize the FULL declared entry regardless of
        # what the caller actually needs (C2b). 64 bytes is generous
        # headroom over "application/epub+zip" (20 bytes exactly).
        try:
            with zf.open(first) as member:
                mime_bytes = member.read(64)
                # Confirm nothing more follows — a legitimate mimetype
                # entry is exactly 20 bytes; reading one extra byte proves
                # (without unbounded reads) that it's larger than claimed.
                extra = member.read(1)
        except (RuntimeError, NotImplementedError, BadZipFile) as exc:
            # Encrypted-entry / unsupported-compression errors that the
            # flag_bits pre-check above didn't already catch (defense in
            # depth — never let zipfile's internals escape as a 500).
            logger.info("epub mimetype read rejected: %s", exc)
            return False

        if extra:
            return False  # entry is longer than any legitimate mimetype value
        if mime_bytes != b"application/epub+zip":
            return False

        return True


def _sniff_and_ext(path: Path, claimed_ext: str) -> str:
    """Sniff the bytes at `path` and return the extension implied by their
    ACTUAL content (I3) — never the client-supplied filename. The stored
    extension always comes from the sniff result, but the sniff itself is
    checked against `claimed_ext` (already allowlist-validated by the
    caller): content must match what the upload claimed to be, so a PDF
    uploaded as "evil.epub" is rejected as a mismatch rather than silently
    reinterpreted/renamed to whatever it actually sniffs as. Raises
    HTTPException(400) if the content doesn't match its claimed type."""
    if claimed_ext == "pdf" and _sniff_pdf(path):
        return "pdf"
    if claimed_ext == "epub" and _sniff_epub(path):
        return "epub"
    _reject(_GENERIC_UPLOAD_ERROR)


def save_ebook_file(owner_id: int, upload: UploadFile, db,
                    allowed: "set[str] | None" = None) -> "tuple[str, int]":
    """Validate + store one uploaded ebook/sample. Returns
    (path relative to EBOOKS_ROOT as a posix string, size in bytes).
    Raises HTTPException 400/413 on any violation, leaving nothing on disk.

    `db`: a SQLAlchemy session, REQUIRED — used to enforce the per-owner
    aggregate cap against real Ebook rows (I1 — never an on-disk walk).
    This is a required positional argument, not an optional one: an
    earlier revision made it optional with a "skip the cap if omitted"
    fallback, which is a fail-open pattern (a caller that simply forgets
    the argument silently loses the per-owner quota enforcement) — exactly
    what this hardening pass exists to eliminate. Every caller, including
    tests that don't care about the cap, must pass a session (a fresh
    zero-row session is fine — the cap check against zero existing bytes
    is cheap and still exercises the real code path)."""
    # M4/New-3: owner_id must be a genuine int (bool excluded — True/False
    # are technically ints in Python but "owner 1"/"owner 0" from a stray
    # boolean is never a legitimate caller intent) OR a pure-digit str (the
    # common "came through as a path/form param" shape). Anything else —
    # float (1.9 silently truncating to 1 is a correctness bug hiding a
    # caller mistake), bytes, or a non-digit string — is a clean 400, never
    # coerced. This is deliberately narrower than Python's own int(x): no
    # float truncation, no bytes support, no leading/trailing-whitespace or
    # sign tolerance on strings.
    if isinstance(owner_id, bool):
        _reject("Invalid owner")
    elif isinstance(owner_id, int):
        pass
    elif isinstance(owner_id, str) and owner_id.isdigit():
        owner_id = int(owner_id)
    else:
        _reject("Invalid owner")

    allowed = allowed if allowed is not None else ALLOWED_EXTENSIONS

    # New-2: a non-str filename (e.g. bytes) must be a clean 400, never an
    # escaping TypeError from the str-only .rsplit()/`"." in name` below —
    # same posture as the owner_id guard above.
    if upload.filename is not None and not isinstance(upload.filename, str):
        _reject("Invalid filename")

    name = upload.filename or ""
    # The client filename is used ONLY for this early allowlist pre-check
    # (fast, cheap rejection of obviously-wrong uploads) — it is NEVER
    # echoed back in an error, and it never decides the stored extension
    # (I3). "." not in name / no trailing extension -> fall through to the
    # generic rejection below without quoting the filename anywhere.
    claimed_ext = name.rsplit(".", 1)[1].lower() if "." in name else ""
    if claimed_ext not in allowed:
        _reject(_GENERIC_UPLOAD_ERROR)

    dest_dir = _owner_dir(owner_id)
    dest_dir.mkdir(parents=True, exist_ok=True)

    # I1: sweep abandoned .part files from earlier dead requests before
    # doing anything else in this owner's directory.
    reap_stale_parts(dest_dir)

    tmp = dest_dir / f"{uuid.uuid4().hex}.part"

    # Normalize-and-reassert BEFORE writing. uuid names make traversal
    # impossible by construction; re-assert anyway (h5p_service posture).
    root = EBOOKS_ROOT.resolve()
    resolved = tmp.resolve()
    if root not in resolved.parents:
        raise HTTPException(status_code=500,
                            detail="Storage path escaped the ebooks root")

    size = 0
    try:
        with open(tmp, "wb") as out:
            while True:
                chunk = upload.file.read(_CHUNK)
                if not chunk:
                    break
                size += len(chunk)
                if size > MAX_FILE_BYTES:
                    raise HTTPException(
                        status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                        detail=f"File exceeds the {MAX_FILE_BYTES} byte cap")
                out.write(chunk)
        if size == 0:
            _reject("Uploaded file is empty")

        # I3: the extension is decided by sniffing the bytes now on disk —
        # never by the client filename. claimed_ext (already allowlist-
        # checked above) says what the upload CLAIMS to be; the sniff
        # confirms the bytes actually match that claim.
        ext = _sniff_and_ext(tmp, claimed_ext)

        # Per-owner aggregate cap AGAINST DB ROWS (I1), never an on-disk
        # walk. This upload's own bytes aren't recorded as an Ebook row
        # yet, so add them to the total already on record. ALWAYS runs —
        # db is a required argument, so there is no skip branch here.
        current_total = owner_total_bytes(db, owner_id)
        if current_total + size > MAX_OWNER_TOTAL_BYTES:
            raise HTTPException(
                status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                detail=f"This upload would exceed your {MAX_OWNER_TOTAL_BYTES} "
                       "byte library storage cap. Delete unused files first.")

        final = dest_dir / f"{uuid.uuid4().hex}.{ext}"
        final_resolved = final.resolve()
        if root not in final_resolved.parents:
            raise HTTPException(status_code=500,
                                detail="Storage path escaped the ebooks root")
        tmp.rename(final)
    except Exception:
        tmp.unlink(missing_ok=True)
        raise
    return final.relative_to(EBOOKS_ROOT).as_posix(), size


def resolve_ebook_path(rel_path: str) -> Path:
    """Resolve a stored relative path for serving; 404 on anything that
    normalizes outside EBOOKS_ROOT or doesn't exist. NEVER serve a path
    that didn't come through here."""
    root = EBOOKS_ROOT.resolve()
    candidate = (EBOOKS_ROOT / rel_path).resolve()
    if candidate == root or root not in candidate.parents:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                            detail="File not found")
    if not candidate.is_file():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                            detail="File not found")
    return candidate


def delete_stored_file(rel_path: "str | None") -> None:
    """Best-effort removal of a replaced/deleted blob. Never raises — a
    stale file on disk is an ops nuisance, not a request failure."""
    if not rel_path:
        return
    try:
        root = EBOOKS_ROOT.resolve()
        target = (EBOOKS_ROOT / rel_path).resolve()
        if target != root and root in target.parents:
            target.unlink(missing_ok=True)
    except OSError:
        logger.warning("could not delete stored ebook file %s", rel_path)
