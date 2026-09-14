"""H5P package validation + extraction pipeline (plan Task 4, spec B3/B4).

This is the security-critical core of the H5P feature. An instructor-supplied
`.h5p`/`.zip` package is untrusted input — it is a zip archive that may
contain arbitrary paths, arbitrarily large declared/actual sizes, symlinks,
or disallowed executable content. `validate_and_extract` rejects anything
suspicious BEFORE writing a single byte to disk, then enforces the same caps
again while streaming bytes out during extraction (a zip's *declared* header
sizes can lie — CRC/uncompressed-size fields are attacker-controlled — so the
size guard must also apply to bytes actually read, not just what the
central directory claims).

Extensionless entries (e.g. `LICENSE`, `.htaccess`-style dotfiles, `README`)
are SKIPPED rather than rejected — real lumi.education/h5p.org packages
legitimately ship these, and rejecting a whole otherwise-valid package over a
license file serves no security purpose. "Skipped" means exactly that:
absent from the extracted output, never written to disk, and not fatal to
the rest of the package. Any entry that DOES carry an extension (including
one this module doesn't recognize) is still held to the full allowlist below
and REJECTS the whole package if it doesn't match — the skip treatment is
reserved for names with no extension at all, never for "looks like content
but isn't allowlisted".

Extracted assets land under `uploads/h5p/{public_id}/` and are served by the
existing static `/uploads` mount. Per spec B3 this is acceptable ONLY because
the frontend never renders H5P content directly — it always goes through a
`<iframe sandbox="allow-scripts">` (no `allow-same-origin`) pointing at a
dedicated static player page, so the untrusted JS this pipeline extracts can
never read the app's cookies/DOM/localStorage even though its files are
served from the same origin. This module's job stops at "the files on disk
are safe to serve statically" — it has no opinion on how they're framed.
"""
from __future__ import annotations

import json
import secrets
import shutil
import zipfile
from dataclasses import dataclass
from pathlib import Path, PureWindowsPath
from typing import Optional


class H5PValidationError(Exception):
    """Raised for any rejected package. `.detail` is safe to show the caller."""

    def __init__(self, detail: str):
        self.detail = detail
        super().__init__(detail)


# ---------------------------------------------------------------------------
# Limits (spec B4, plan Task 4 item 3)
# ---------------------------------------------------------------------------
MAX_MEMBER_UNCOMPRESSED_BYTES = 50 * 1024 * 1024        # 50MB per file
MAX_TOTAL_UNCOMPRESSED_BYTES = 300 * 1024 * 1024        # 300MB total (zip-bomb guard)
MAX_FILE_COUNT = 2000

# Extension allowlist for files *inside* the package. Nested .h5p/.zip are
# deliberately NOT in this list — H5P subcontent can legitimately embed
# other H5P packages, but extracting/recursing into a nested archive here
# would reopen every one of these checks against untrusted, unvalidated
# content one level down. Rejecting the whole upload is simpler and safe;
# an author who needs nested content re-exports it as a single package.
ALLOWED_EXTENSIONS = {
    ".html", ".js", ".css", ".json", ".svg", ".png", ".jpg", ".jpeg", ".gif",
    ".webp", ".mp3", ".mp4", ".wav", ".ogg", ".woff", ".woff2", ".ttf",
    ".otf", ".eot", ".vtt", ".csv", ".txt", ".md",
}
# h5p.json itself has no extension check exemption needed (.json is allowed).
DISALLOWED_ARCHIVE_EXTENSIONS = {".h5p", ".zip"}

# Symlink detection: the upper 16 bits of external_attr hold the Unix file
# mode when the archive was created on a Unix-like system (bit set by
# zipfile per the ZIP spec's "external file attributes" field, host system
# 3 = Unix). S_IFLNK = 0o120000.
_S_IFLNK = 0o120000
_UNIX_MODE_MASK = 0xFFFF0000


def generate_public_id() -> str:
    """Opaque, unguessable content id used in URLs and on disk. Never derived
    from the owner/course id (same convention as live_class_service.
    generate_room_name / certificate_service._generate_certificate_id)."""
    return secrets.token_hex(16)


def _is_symlink(info: zipfile.ZipInfo) -> bool:
    mode = (info.external_attr & _UNIX_MODE_MASK) >> 16
    return bool(mode) and (mode & 0o170000) == _S_IFLNK


def _normalized_member_path(name: str) -> Optional[Path]:
    """Return a safe, normalized relative Path for a zip member name, or
    None if the name is unsafe (absolute, drive letter, traversal, or
    otherwise escapes the extraction root once resolved).

    Zip member names are always '/'-separated per the ZIP spec regardless of
    the platform that created the archive, but a malicious archive can still
    smuggle a Windows drive letter ("C:/evil") or backslashes — PureWindowsPath
    catches both an explicit drive and backslash separators that PurePosixPath
    would otherwise treat as a literal filename character.
    """
    if not name or name.endswith("/"):
        return None  # directory entries handled by caller, not a file path
    raw = name.replace("\\", "/")

    # Reject absolute paths (leading '/') outright.
    if raw.startswith("/"):
        return None

    # Reject any component that looks like a Windows drive letter or UNC
    # path even on a POSIX extraction host — the archive could be opened by
    # any OS.
    win_path = PureWindowsPath(raw)
    if win_path.drive or win_path.root:
        return None

    parts = [p for p in raw.split("/") if p not in ("", ".")]
    if not parts:
        return None
    if any(p == ".." for p in parts):
        return None
    # Reject NUL bytes / control chars defensively.
    if any("\x00" in p for p in parts):
        return None

    candidate = Path(*parts)
    # Final belt-and-braces check: resolving relative to a fixed dummy root
    # must stay inside that root.
    dummy_root = Path("__h5p_root__")
    resolved = (dummy_root / candidate).resolve()
    if dummy_root.resolve() not in resolved.parents and resolved != dummy_root.resolve():
        return None
    return candidate


@dataclass
class H5PExtractionResult:
    public_id: str
    library: Optional[str]
    size_bytes: int
    file_count: int
    dest_dir: Path


def peek_declared_total_size(zip_path: Path) -> int:
    """Sum of every member's DECLARED uncompressed size, without extracting
    anything. Used by callers that want to pre-flight a per-owner aggregate
    disk-usage cap before committing to a full validate_and_extract call.

    This is a cheap advisory number, not a security boundary — declared
    sizes can lie (see validate_and_extract's pass-2 streamed enforcement
    for the check that actually matters). Raises H5PValidationError if the
    file isn't a readable zip at all.
    """
    zip_path = Path(zip_path)
    if not zipfile.is_zipfile(zip_path):
        raise H5PValidationError("Not a valid zip/h5p package")
    try:
        with zipfile.ZipFile(zip_path) as zf:
            return sum(info.file_size for info in zf.infolist() if not info.is_dir())
    except zipfile.BadZipFile:
        raise H5PValidationError("Corrupt zip/h5p package")


def validate_and_extract(zip_path: Path, dest_dir: Path) -> H5PExtractionResult:
    """Validate an uploaded `.h5p`/`.zip` package and, only if every check
    passes, extract it to `dest_dir` (created fresh — must not already
    exist/contain anything, caller is responsible for choosing a fresh
    per-content directory such as uploads/h5p/{public_id}/).

    Raises H5PValidationError on any violation. On failure, `dest_dir` is
    guaranteed to not exist (nothing partially extracted survives).
    """
    zip_path = Path(zip_path)
    dest_dir = Path(dest_dir)

    if dest_dir.exists() and any(dest_dir.iterdir()):
        raise H5PValidationError("Extraction destination is not empty")

    if not zipfile.is_zipfile(zip_path):
        raise H5PValidationError("Not a valid zip/h5p package")

    try:
        zf = zipfile.ZipFile(zip_path)
    except zipfile.BadZipFile:
        raise H5PValidationError("Corrupt zip/h5p package")

    with zf:
        infolist = zf.infolist()

        if len(infolist) > MAX_FILE_COUNT:
            raise H5PValidationError(
                f"Package contains too many files ({len(infolist)} > {MAX_FILE_COUNT})"
            )

        # ---- Pass 1: validate every member using the DECLARED metadata
        # before extracting anything. A lying header must not let a bad
        # member's bytes hit disk even transiently. ----
        total_declared = 0
        safe_members: list[tuple[zipfile.ZipInfo, Path]] = []
        seen_rel_paths: set = set()
        has_root_h5p_json = False

        for info in infolist:
            name = info.filename

            if info.is_dir() or name.endswith("/"):
                # Directory entries carry no bytes and are never extracted
                # as files (target.parent.mkdir in pass 2 creates whatever
                # directories a real file member needs), so they are
                # skipped here WITHOUT a path-safety check — a directory
                # entry alone can never write anywhere.
                continue

            if _is_symlink(info):
                raise H5PValidationError(f"Symlinks are not allowed in the package: {name}")

            safe_rel = _normalized_member_path(name)
            if safe_rel is None:
                raise H5PValidationError(f"Unsafe path in package: {name}")

            if safe_rel in seen_rel_paths:
                # A zip may legally contain two entries with the same name
                # (most tools refuse to produce one, but the format doesn't
                # forbid it) — extracting both silently overwrites the
                # first with the second, which is exactly the kind of
                # ambiguity a hardened extractor shouldn't paper over.
                raise H5PValidationError(f"Duplicate entry in package: {name}")
            seen_rel_paths.add(safe_rel)

            ext = safe_rel.suffix.lower()
            if ext == "":
                # Extensionless entries are typically plain metadata that
                # real lumi.education/h5p.org packages legitimately ship
                # (LICENSE, .htaccess-style dotfiles, README) — reject
                # outright and authors of otherwise-valid packages hit a
                # wall for no security benefit. These are SKIPPED (not
                # extracted, not fatal) rather than rejected: anything
                # skipped is simply absent from the extracted output.
                # Anything that DOES carry an extension is still held to
                # the full allowlist below — only a name with no extension
                # at all gets this pass.
                continue
            if ext in DISALLOWED_ARCHIVE_EXTENSIONS:
                raise H5PValidationError(
                    f"Nested archive files are not allowed: {name}"
                )
            if ext not in ALLOWED_EXTENSIONS:
                raise H5PValidationError(
                    f"Disallowed file type in package: {name}"
                )

            declared_size = info.file_size
            if declared_size > MAX_MEMBER_UNCOMPRESSED_BYTES:
                raise H5PValidationError(
                    f"File too large in package: {name} "
                    f"({declared_size} > {MAX_MEMBER_UNCOMPRESSED_BYTES} bytes)"
                )
            total_declared += declared_size
            if total_declared > MAX_TOTAL_UNCOMPRESSED_BYTES:
                raise H5PValidationError(
                    "Package's total uncompressed size exceeds the "
                    f"{MAX_TOTAL_UNCOMPRESSED_BYTES} byte limit"
                )

            if safe_rel == Path("h5p.json"):
                has_root_h5p_json = True

            safe_members.append((info, safe_rel))

        if not has_root_h5p_json:
            raise H5PValidationError("Package is missing h5p.json at its root")

        # ---- Read + parse h5p.json for mainLibrary (still pre-extraction). ----
        h5p_json_info = next(info for info, rel in safe_members if rel == Path("h5p.json"))
        try:
            raw = zf.read(h5p_json_info)
        except Exception as exc:
            raise H5PValidationError(f"Could not read h5p.json: {exc}")
        try:
            manifest = json.loads(raw.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise H5PValidationError(f"h5p.json is not valid JSON: {exc}")
        main_library = manifest.get("mainLibrary") if isinstance(manifest, dict) else None
        if main_library is not None and not isinstance(main_library, str):
            main_library = None
        if main_library is not None:
            # Truncate at the source so every caller gets an already-safe
            # value — H5PContent.library is String(120); an h5p.json with an
            # absurdly long mainLibrary string must not risk a DB-level
            # truncation/length error downstream.
            main_library = main_library[:120]

        # ---- Pass 2: extract, re-enforcing size caps against ACTUAL bytes
        # streamed out (declared sizes in the central directory / local file
        # header are attacker-controlled and can understate reality). ----
        dest_dir.mkdir(parents=True, exist_ok=True)
        actual_total = 0
        try:
            for info, rel in safe_members:
                target = dest_dir / rel
                target.parent.mkdir(parents=True, exist_ok=True)

                member_bytes = 0
                chunk_size = 1024 * 1024
                with zf.open(info) as src, target.open("wb") as out:
                    while True:
                        chunk = src.read(chunk_size)
                        if not chunk:
                            break
                        member_bytes += len(chunk)
                        actual_total += len(chunk)
                        if member_bytes > MAX_MEMBER_UNCOMPRESSED_BYTES:
                            raise H5PValidationError(
                                f"File exceeded the per-file size limit during "
                                f"extraction (declared size lied): {info.filename}"
                            )
                        if actual_total > MAX_TOTAL_UNCOMPRESSED_BYTES:
                            raise H5PValidationError(
                                "Package exceeded the total size limit during "
                                "extraction (declared sizes lied)"
                            )
                        out.write(chunk)
        except H5PValidationError as exc:
            # Nothing partially extracted may survive a rejected package.
            shutil.rmtree(dest_dir, ignore_errors=True)
            raise H5PValidationError(exc.detail) from None
        except Exception as exc:
            shutil.rmtree(dest_dir, ignore_errors=True)
            raise H5PValidationError(f"Extraction failed: {exc}") from None

        return H5PExtractionResult(
            public_id=dest_dir.name,
            library=main_library,
            size_bytes=actual_total,
            file_count=len(safe_members),
            dest_dir=dest_dir,
        )
