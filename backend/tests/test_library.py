"""Digital Library backend (docs/superpowers/specs/2026-09-03-digital-library-design.md).

Grows across plan Tasks 1-7: models/migration, upload hardening, instructor
CRUD + ownership, public store + download gates, payment extension,
webhook/sweeper convergence + free claim, suggestions.
SQLite in-memory per repo pattern (see conftest.py).
"""
import io
import os
import zipfile
from pathlib import Path

import pyotp
import pytest
from fastapi import UploadFile

from app.core import totp
from app.models.course import Course
from app.models.ebook import EBOOK_CATEGORIES, Ebook, EbookGrant, effective_price_inr
from app.models.payment import Order, OrderItem, Payment
from app.models.user import User


def _admin_headers(client, db, admin):
    """Admin logins require TOTP 2FA — enrol a secret and send the current
    code (mirrors test_games._admin_headers / test_h5p._admin_headers)."""
    admin.totp_enabled = True
    admin.totp_secret = totp.generate_secret()
    db.commit()
    r = client.post(
        "/api/v1/auth/login",
        json={
            "email": admin.user_email,
            "password": admin._test_password,
            "otp_code": pyotp.TOTP(admin.totp_secret).now(),
        },
    )
    assert r.status_code == 200, r.text
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


# ----- factories --------------------------------------------------------------

def _make_approved_instructor(db, make_user, email):
    from app.models.user import InstructorProfile
    instructor = make_user(role="instructor", email=email)
    profile = db.query(InstructorProfile).filter_by(user_id=instructor.id).first()
    if profile:
        profile.is_approved = True
    else:
        db.add(InstructorProfile(user_id=instructor.id, is_approved=True))
    db.commit()
    return instructor


def _make_ebook(db, owner, *, title="Demo Ebook", category="book", price=199,
                discount=None, status="draft", file_path=None, sample_path=None,
                tags=None, course_id=None):
    ebook = Ebook(
        owner_id=owner.id, title=title, slug="pending", category=category,
        price_inr=price, discount_price_inr=discount, status=status,
        file_path=file_path, sample_path=sample_path,
        file_size_bytes=1024 if file_path else 0,
        concept_tags=tags or [], course_id=course_id,
    )
    db.add(ebook)
    db.flush()
    ebook.slug = f"{title.lower().replace(' ', '-')}-{ebook.id}"
    db.commit()
    db.refresh(ebook)
    return ebook


def _grant(db, ebook, user, *, order_id=None, source="purchase"):
    g = EbookGrant(ebook_id=ebook.id, user_id=user.id, order_id=order_id, source=source)
    db.add(g)
    db.commit()
    db.refresh(g)
    return g


# Tiny REAL file payloads for upload tests (magic bytes must be genuine).
PDF_BYTES = b"%PDF-1.4\n1 0 obj\n<< /Type /Catalog >>\nendobj\ntrailer\n<< >>\n%%EOF\n"


def _epub_bytes(mimetype=b"application/epub+zip"):
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        zf.writestr("mimetype", mimetype)
        zf.writestr("META-INF/container.xml", "<container/>")
    return buf.getvalue()


# ============================================================================
# Task 1: models + migration columns
# ============================================================================


class TestEbookModels:
    def test_ebook_defaults_and_effective_price(self, db, make_user):
        owner = _make_approved_instructor(db, make_user, "lib-owner@example.com")
        ebook = _make_ebook(db, owner, price=499)
        assert ebook.status == "draft"
        assert ebook.category in EBOOK_CATEGORIES
        assert ebook.concept_tags == []
        assert effective_price_inr(ebook) == 499
        ebook.discount_price_inr = 299
        assert effective_price_inr(ebook) == 299

    def test_grant_unique_per_user(self, db, make_user):
        owner = _make_approved_instructor(db, make_user, "lib-owner2@example.com")
        student = make_user(role="student")
        ebook = _make_ebook(db, owner, status="published")
        _grant(db, ebook, student)
        from sqlalchemy.exc import IntegrityError
        db.add(EbookGrant(ebook_id=ebook.id, user_id=student.id, source="admin"))
        with pytest.raises(IntegrityError):
            db.commit()
        db.rollback()

    def test_order_and_order_item_ebook_columns(self, db, make_user):
        owner = _make_approved_instructor(db, make_user, "lib-owner3@example.com")
        student = make_user(role="student")
        ebook = _make_ebook(db, owner, status="published")
        from app.models.payment import OrderStatus
        order = Order(user_id=student.id, ebook_id=ebook.id, order_key="EBK_TEST1",
                      order_status=OrderStatus.COMPLETED, total_amount=199)
        db.add(order)
        db.flush()
        # course_id is now nullable: an ebook line has no course.
        db.add(OrderItem(order_id=order.id, course_id=None, ebook_id=ebook.id,
                         order_item_name=ebook.title, order_item_type="ebook_item",
                         quantity=1, subtotal=199, total=199))
        db.commit()
        item = db.query(OrderItem).filter(OrderItem.ebook_id == ebook.id).one()
        assert item.course_id is None
        assert item.order_item_type == "ebook_item"


class TestMigration0005:
    def test_upgrade_creates_tables_and_columns(self, tmp_path):
        """Run 0005's upgrade() against a bare SQLite file DB that already has
        the FK-target tables (mirrors test_games.py's TestMigration0004)."""
        import sqlalchemy as sa
        from alembic.migration import MigrationContext
        from alembic.operations import Operations
        import importlib.util
        from pathlib import Path

        engine = sa.create_engine(f"sqlite:///{tmp_path / 'mig.db'}")
        with engine.begin() as conn:
            conn.execute(sa.text("CREATE TABLE users (id INTEGER PRIMARY KEY)"))
            conn.execute(sa.text("CREATE TABLE courses (id INTEGER PRIMARY KEY)"))
            conn.execute(sa.text("CREATE TABLE orders (id INTEGER PRIMARY KEY)"))
            conn.execute(sa.text(
                "CREATE TABLE order_items (id INTEGER PRIMARY KEY, "
                "order_id INTEGER NOT NULL, course_id INTEGER NOT NULL)"))
        path = Path(__file__).resolve().parents[1] / "alembic" / "versions" / "0005_digital_library.py"
        spec = importlib.util.spec_from_file_location("mig_0005", path)
        mig = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mig)

        with engine.connect() as conn:
            ctx = MigrationContext.configure(conn)
            with Operations.context(ctx):
                mig.upgrade()
            conn.commit()

        insp = sa.inspect(engine)
        assert insp.has_table("ebooks")
        assert insp.has_table("ebook_grants")
        ebook_cols = {c["name"] for c in insp.get_columns("ebooks")}
        assert {"id", "owner_id", "title", "slug", "description", "category",
                "price_inr", "discount_price_inr", "cover_image", "file_path",
                "file_size_bytes", "page_count", "sample_path", "concept_tags",
                "course_id", "status", "created_at", "updated_at"} <= ebook_cols
        grant_cols = {c["name"] for c in insp.get_columns("ebook_grants")}
        assert {"id", "ebook_id", "user_id", "order_id", "source", "granted_at"} <= grant_cols
        order_cols = {c["name"] for c in insp.get_columns("orders")}
        assert "ebook_id" in order_cols
        item_cols = {c["name"]: c for c in insp.get_columns("order_items")}
        assert "ebook_id" in item_cols
        assert item_cols["course_id"]["nullable"] is True  # relaxed by 0005
        uniques = {u["name"] for u in insp.get_unique_constraints("ebook_grants")}
        assert "uq_ebook_grants_ebook_user" in uniques

    def test_upgrade_relaxes_course_id_on_preseeded_db_stamped_at_0004(self, tmp_path):
        """Prove the order_items.course_id nullable-relaxation actually works
        against a REAL pre-existing app schema (not the bare synthetic tables
        above): build the full schema via create_all(), insert a NOT-NULL-era
        order_item row, stamp the DB at 0004 (mirroring how a real deployed
        DB would already be, pre-this-migration), run `alembic upgrade head`
        via the CLI, and confirm course_id is now nullable and the old row
        (with its NOT NULL course_id already set) survived untouched.
        """
        import os

        import sqlalchemy as sa
        from alembic import command
        from alembic.config import Config
        from pathlib import Path

        BACKEND_DIR = Path(__file__).resolve().parents[1]
        db_file = tmp_path / "scratch_0004.sqlite3"
        db_url = f"sqlite:///{db_file}"

        # Build the FULL current app schema (as init_db()'s create_all would),
        # then seed one legacy course-only order_item row before 0005 exists.
        from app.core.database import Base
        from app import models  # noqa: F401
        from app.models.user import User
        from app.models.course import Course
        from app.models.payment import Order, OrderItem, OrderStatus

        engine = sa.create_engine(db_url, connect_args={"check_same_thread": False})
        Base.metadata.create_all(bind=engine)

        from sqlalchemy.orm import sessionmaker
        Session = sessionmaker(bind=engine)
        session = Session()
        instructor = User(user_login="mig-instr", user_pass="x", user_nicename="mig-instr",
                          user_email="mig-instr@example.com", display_name="mig-instr")
        session.add(instructor)
        session.commit()
        course = Course(post_author=instructor.id, post_title="Migration Course",
                        course_price_type="paid", course_price=500.0)
        session.add(course)
        student = User(user_login="mig-student", user_pass="x", user_nicename="mig-student",
                       user_email="mig-student@example.com", display_name="mig-student")
        session.add(student)
        session.commit()
        order = Order(user_id=student.id, order_key="RZP_MIG_TEST",
                      order_status=OrderStatus.COMPLETED, total_amount=500)
        session.add(order)
        session.commit()
        course_id = course.id
        legacy_item = OrderItem(order_id=order.id, course_id=course_id,
                                order_item_name="Migration Course", order_item_type="line_item",
                                quantity=1, subtotal=500, total=500)
        session.add(legacy_item)
        session.commit()
        legacy_item_id = legacy_item.id
        session.close()
        engine.dispose()

        cfg = Config(str(BACKEND_DIR / "alembic.ini"))
        cfg.set_main_option("script_location", str(BACKEND_DIR / "alembic"))
        os.environ["DATABASE_URL"] = db_url
        try:
            # Stamp at 0004 — this DB already has the full schema (created_all
            # includes ebooks/ebook_grants/order_items.ebook_id too, since the
            # models were already updated for 0005), mirroring a real deploy
            # where create_all() ran ahead of `alembic upgrade head` and
            # already brought the schema current; the stamp records history
            # as if only 0004 had run.
            command.stamp(cfg, "0004")

            command.upgrade(cfg, "head")

            engine = sa.create_engine(db_url)
            insp = sa.inspect(engine)
            item_cols = {c["name"]: c for c in insp.get_columns("order_items")}
            assert item_cols["course_id"]["nullable"] is True
            assert "ebook_id" in item_cols

            with engine.connect() as conn:
                row = conn.execute(
                    sa.text("SELECT course_id, ebook_id FROM order_items WHERE id = :id"),
                    {"id": legacy_item_id},
                ).fetchone()
            assert row[0] == course_id
            assert row[1] is None
            engine.dispose()

            # Downgrade proof: base of this migration removes ebooks/
            # ebook_grants and the ebook_id columns without erroring.
            command.downgrade(cfg, "0004")
            engine = sa.create_engine(db_url)
            insp = sa.inspect(engine)
            assert not insp.has_table("ebook_grants")
            assert not insp.has_table("ebooks")
            engine.dispose()
        finally:
            os.environ.pop("DATABASE_URL", None)


# ============================================================================
# Task 2: upload hardening
# ============================================================================

from fastapi import HTTPException, UploadFile  # noqa: E402


@pytest.fixture
def ebooks_root(tmp_path, monkeypatch):
    """Point the storage service (and everything importing it as a MODULE)
    at a throwaway root. Routers must use `from app.services import
    library_storage` + attribute access so this monkeypatch reaches them."""
    from app.services import library_storage
    root = tmp_path / "ebooks"
    monkeypatch.setattr(library_storage, "EBOOKS_ROOT", root)
    return root


def _upload(name: str, data: bytes) -> UploadFile:
    return UploadFile(filename=name, file=io.BytesIO(data))


class TestUploadHardening:
    def test_valid_pdf_saved_with_uuid_name(self, ebooks_root, db):
        from app.services import library_storage
        rel, size = library_storage.save_ebook_file(7, _upload("My Notes.pdf", PDF_BYTES), db)
        assert size == len(PDF_BYTES)
        assert rel.startswith("7/")
        assert "My Notes" not in rel and "my notes" not in rel  # filename never trusted
        assert rel.endswith(".pdf")
        assert (ebooks_root / rel).is_file()

    def test_valid_epub_saved(self, ebooks_root, db):
        from app.services import library_storage
        rel, _ = library_storage.save_ebook_file(7, _upload("book.epub", _epub_bytes()), db)
        assert rel.endswith(".epub")

    @pytest.mark.parametrize("name,data", [
        ("notes.txt", PDF_BYTES),                        # bad extension
        ("noext", PDF_BYTES),                            # no extension
        ("evil.pdf.exe", PDF_BYTES),                     # ext taken from LAST segment
        ("fake.pdf", b"MZ\x90\x00 not a pdf at all"),   # wrong magic bytes
        ("fake.epub", PDF_BYTES),                        # pdf bytes in .epub clothing
        ("nomime.epub", b"PK\x03\x04broken"),            # zip magic, not a real zip
        ("empty.pdf", b""),                              # empty
    ])
    def test_rejected_uploads(self, ebooks_root, db, name, data):
        from app.services import library_storage
        with pytest.raises(HTTPException) as exc:
            library_storage.save_ebook_file(7, _upload(name, data), db)
        assert exc.value.status_code in (400, 413)
        # nothing durable left behind (no .part or final files)
        leftovers = list(ebooks_root.rglob("*")) if ebooks_root.exists() else []
        assert not [p for p in leftovers if p.is_file()]

    def test_epub_wrong_mimetype_entry_rejected(self, ebooks_root, db):
        from app.services import library_storage
        bad = _epub_bytes(mimetype=b"application/zip")
        with pytest.raises(HTTPException) as exc:
            library_storage.save_ebook_file(7, _upload("book.epub", bad), db)
        assert exc.value.status_code == 400

    def test_oversize_rejected(self, ebooks_root, db, monkeypatch):
        from app.services import library_storage
        monkeypatch.setattr(library_storage, "MAX_FILE_BYTES", 16)
        with pytest.raises(HTTPException) as exc:
            library_storage.save_ebook_file(7, _upload("big.pdf", PDF_BYTES), db)
        assert exc.value.status_code == 413

    def test_per_owner_total_cap(self, ebooks_root, monkeypatch, db, make_user):
        # I1: the cap is computed from DB rows (ebooks.file_size_bytes), not
        # an on-disk walk — so this test records each saved file as an
        # Ebook row (as a real caller/router would) to build up usage.
        from app.services import library_storage
        monkeypatch.setattr(library_storage, "MAX_OWNER_TOTAL_BYTES",
                            len(PDF_BYTES) + 10)
        owner = _make_approved_instructor(db, make_user, "cap-flow-owner@example.com")
        other = _make_approved_instructor(db, make_user, "cap-flow-owner2@example.com")

        rel, size = library_storage.save_ebook_file(owner.id, _upload("a.pdf", PDF_BYTES), db)  # fits
        _make_ebook(db, owner, file_path=rel, status="published")
        # Ebook.file_size_bytes must reflect the real saved size for the cap
        # to mean anything; _make_ebook's default (1024) would overshoot.
        ebook = db.query(Ebook).filter_by(file_path=rel).one()
        ebook.file_size_bytes = size
        db.commit()

        with pytest.raises(HTTPException) as exc:
            library_storage.save_ebook_file(owner.id, _upload("b.pdf", PDF_BYTES), db)  # cap
        assert exc.value.status_code == 413
        # another owner's dir/DB usage is unaffected by owner's usage
        library_storage.save_ebook_file(other.id, _upload("c.pdf", PDF_BYTES), db)

    def test_sample_allowlist_pdf_only(self, ebooks_root, db):
        from app.services import library_storage
        with pytest.raises(HTTPException) as exc:
            library_storage.save_ebook_file(7, _upload("s.epub", _epub_bytes()), db,
                                            allowed={"pdf"})
        assert exc.value.status_code == 400

    def test_resolve_reasserts_root(self, ebooks_root, db):
        from app.services import library_storage
        rel, _ = library_storage.save_ebook_file(7, _upload("ok.pdf", PDF_BYTES), db)
        assert library_storage.resolve_ebook_path(rel).is_file()
        for evil in ("../../etc/passwd", "..\\..\\secrets.pdf", "/etc/passwd"):
            with pytest.raises(HTTPException) as exc:
                library_storage.resolve_ebook_path(evil)
            assert exc.value.status_code == 404

    def test_missing_db_raises_type_error(self, ebooks_root):
        # Round 2 ruling: db is a REQUIRED positional argument with no
        # default and no "skip the cap" branch — a caller that forgets it
        # must get a loud TypeError, never a silent quota bypass.
        from app.services import library_storage
        with pytest.raises(TypeError):
            library_storage.save_ebook_file(7, _upload("ok.pdf", PDF_BYTES))


# ============================================================================
# Task 2 fix round: adversarial-review findings (C1, C2, I1, I2, I3, I4)
# ============================================================================


def _epub_bytes_raw(entries, *, mimetype_first=True, mimetype_stored=True,
                     mimetype_bytes=b"application/epub+zip"):
    """Build epub bytes with full control over entry order/compression, for
    OCF-conformance tests that the innocent `_epub_bytes()` helper can't
    express (last-entry mimetype, deflated mimetype, padded mimetype)."""
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        if mimetype_first:
            if mimetype_stored:
                zf.writestr(zipfile.ZipInfo("mimetype"), mimetype_bytes,
                            zipfile.ZIP_STORED)
            else:
                zf.writestr("mimetype", mimetype_bytes, zipfile.ZIP_DEFLATED)
        for name, data in entries:
            zf.writestr(name, data)
        if not mimetype_first:
            zf.writestr("mimetype", mimetype_bytes)
    return buf.getvalue()


def _encrypted_zip_bytes() -> bytes:
    """A real zip whose 'mimetype' entry has the encryption bit (flag_bits
    0x1) set in its local file header AND central directory — no password
    needed to trigger zf.read()'s RuntimeError, just the flag bit."""
    import struct

    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        zf.writestr("mimetype", b"application/epub+zip")
        zf.writestr("META-INF/container.xml", "<container/>")
    data = bytearray(buf.getvalue())

    # Local file header: signature(4) ver(2) flags(2) ... — flags at offset 6.
    # Central directory header: signature(4) ver_made(2) ver_need(2) flags(2) — flags at offset 8.
    lfh_sig = b"PK\x03\x04"
    cdh_sig = b"PK\x01\x02"
    idx = data.find(lfh_sig)
    assert idx != -1
    flags = struct.unpack_from("<H", data, idx + 6)[0]
    struct.pack_into("<H", data, idx + 6, flags | 0x1)

    idx2 = data.find(cdh_sig)
    assert idx2 != -1
    flags2 = struct.unpack_from("<H", data, idx2 + 8)[0]
    struct.pack_into("<H", data, idx2 + 8, flags2 | 0x1)

    return bytes(data)


class TestC1EncryptedEpubRejected:
    """C1: an EPUB whose entries carry the zip encryption flag bit must be
    cleanly rejected (400), never let RuntimeError/NotImplementedError
    escape as an unhandled 500."""

    def test_encrypted_entry_flag_rejected_cleanly(self, ebooks_root, db):
        from app.services import library_storage
        payload = _encrypted_zip_bytes()
        with pytest.raises(HTTPException) as exc:
            library_storage.save_ebook_file(7, _upload("book.epub", payload), db)
        assert exc.value.status_code == 400
        # nothing durable left behind
        leftovers = list(ebooks_root.rglob("*")) if ebooks_root.exists() else []
        assert not [p for p in leftovers if p.is_file()]


class TestC2ZipBombCaps:
    """C2: entry-count and declared-uncompressed-size caps must reject
    hostile zips BEFORE any unbounded read, and the mimetype read itself
    must be bounded regardless of what the entry declares."""

    def test_too_many_entries_rejected(self, ebooks_root, db, monkeypatch):
        from app.services import library_storage
        monkeypatch.setattr(library_storage, "MAX_EPUB_ENTRIES", 100)
        buf = io.BytesIO()
        with zipfile.ZipFile(buf, "w") as zf:
            zf.writestr(zipfile.ZipInfo("mimetype"), b"application/epub+zip",
                        zipfile.ZIP_STORED)
            for i in range(200):
                zf.writestr(f"f{i}.txt", "x")
        with pytest.raises(HTTPException) as exc:
            library_storage.save_ebook_file(7, _upload("bomb.epub", buf.getvalue()), db)
        assert exc.value.status_code == 400
        leftovers = list(ebooks_root.rglob("*")) if ebooks_root.exists() else []
        assert not [p for p in leftovers if p.is_file()]

    def test_declared_uncompressed_size_over_cap_rejected(self, ebooks_root, db, monkeypatch):
        from app.services import library_storage
        # Inject a modest test cap so we don't need a real 1GB+ payload to
        # exercise the rejection path.
        monkeypatch.setattr(library_storage, "MAX_EPUB_UNCOMPRESSED", 1024)
        buf = io.BytesIO()
        with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
            zf.writestr(zipfile.ZipInfo("mimetype"), b"application/epub+zip",
                        zipfile.ZIP_STORED)
            # Highly compressible content whose DECLARED uncompressed size
            # exceeds the (test) cap while the zip file itself stays tiny.
            zf.writestr("big.txt", b"0" * 5000)
        with pytest.raises(HTTPException) as exc:
            library_storage.save_ebook_file(7, _upload("expand.epub", buf.getvalue()), db)
        assert exc.value.status_code == 400
        leftovers = list(ebooks_root.rglob("*")) if ebooks_root.exists() else []
        assert not [p for p in leftovers if p.is_file()]

    def test_mimetype_entry_declaring_huge_size_rejected_without_allocating(self, ebooks_root, db):
        from app.services import library_storage
        import struct
        import tracemalloc

        # Build a zip whose 'mimetype' local header + central directory both
        # declare an absurd (1 GiB) uncompressed size for that single entry,
        # to prove the cap fires from declared metadata before any read of
        # the entry's bytes — not just that the bytes actually read are capped.
        buf = io.BytesIO()
        with zipfile.ZipFile(buf, "w") as zf:
            zf.writestr(zipfile.ZipInfo("mimetype"), b"application/epub+zip",
                        zipfile.ZIP_STORED)
            zf.writestr("META-INF/container.xml", "<container/>")
        data = bytearray(buf.getvalue())
        huge = 1 * 1024 * 1024 * 1024  # 1 GiB declared, bytes on disk are tiny

        lfh_sig = b"PK\x03\x04"
        cdh_sig = b"PK\x01\x02"
        idx = data.find(lfh_sig)
        assert idx != -1
        # local file header: sig(4) ver(2) flags(2) method(2) time(2) date(2)
        # crc(4) comp_size(4) uncomp_size(4) -> uncomp_size at offset+22
        struct.pack_into("<I", data, idx + 22, huge)

        idx2 = data.find(cdh_sig)
        assert idx2 != -1
        # central dir header: uncomp_size at offset+24
        struct.pack_into("<I", data, idx2 + 24, huge)

        payload = bytes(data)

        tracemalloc.start()
        try:
            with pytest.raises(HTTPException) as exc:
                library_storage.save_ebook_file(7, _upload("hugemime.epub", payload), db)
            current, peak = tracemalloc.get_traced_memory()
        finally:
            tracemalloc.stop()

        assert exc.value.status_code == 400
        assert peak < 50 * 1024 * 1024  # never allocated anywhere near 1GiB
        leftovers = list(ebooks_root.rglob("*")) if ebooks_root.exists() else []
        assert not [p for p in leftovers if p.is_file()]


class TestI1OwnerCapFromDbAndStaleParts:
    """I1: per-owner cap must reflect DB rows (Ebook.file_size_bytes), not an
    on-disk walk that a caller could pad with orphan files; abandoned .part
    files older than the threshold must be reaped at the start of save."""

    def test_owner_total_bytes_reflects_db_not_orphan_files(self, ebooks_root, db, make_user):
        from app.services import library_storage

        owner = _make_approved_instructor(db, make_user, "cap-owner@example.com")
        _make_ebook(db, owner, file_path="7/real.pdf", status="published")
        # DB says 1024 bytes (see _make_ebook's file_size_bytes=1024 default).
        assert library_storage.owner_total_bytes(db, owner.id) == 1024

        # An orphan file directly on disk (never recorded in the DB) must
        # NOT inflate the reported total.
        orphan_dir = ebooks_root / str(owner.id)
        orphan_dir.mkdir(parents=True, exist_ok=True)
        (orphan_dir / "orphan.pdf").write_bytes(b"x" * 999_999)

        assert library_storage.owner_total_bytes(db, owner.id) == 1024

    def test_stale_part_file_reaped_fresh_part_kept(self, ebooks_root):
        from app.services import library_storage
        import os
        import time

        owner_dir = ebooks_root / "7"
        owner_dir.mkdir(parents=True, exist_ok=True)
        stale = owner_dir / "stale.pdf.part"
        fresh = owner_dir / "fresh.pdf.part"
        stale.write_bytes(b"x")
        fresh.write_bytes(b"y")
        old_time = time.time() - 7200  # 2 hours old
        os.utime(stale, (old_time, old_time))

        library_storage.reap_stale_parts(owner_dir, older_than_seconds=3600)

        assert not stale.exists()
        assert fresh.exists()


class TestI2StrictOcfMimetypeCheck:
    """I2: the OCF spec requires 'mimetype' to be the FIRST entry, stored
    (uncompressed), with the exact byte content 'application/epub+zip' — no
    whitespace tolerance, no accepting it from any other position."""

    def test_mimetype_as_last_entry_rejected(self, ebooks_root, db):
        from app.services import library_storage
        payload = _epub_bytes_raw([("META-INF/container.xml", "<container/>")],
                                   mimetype_first=False)
        with pytest.raises(HTTPException) as exc:
            library_storage.save_ebook_file(7, _upload("book.epub", payload), db)
        assert exc.value.status_code == 400

    def test_mimetype_deflated_rejected(self, ebooks_root, db):
        from app.services import library_storage
        payload = _epub_bytes_raw([("META-INF/container.xml", "<container/>")],
                                   mimetype_first=True, mimetype_stored=False)
        with pytest.raises(HTTPException) as exc:
            library_storage.save_ebook_file(7, _upload("book.epub", payload), db)
        assert exc.value.status_code == 400

    def test_mimetype_whitespace_padded_rejected(self, ebooks_root, db):
        from app.services import library_storage
        payload = _epub_bytes_raw([("META-INF/container.xml", "<container/>")],
                                   mimetype_bytes=b"application/epub+zip \n")
        with pytest.raises(HTTPException) as exc:
            library_storage.save_ebook_file(7, _upload("book.epub", payload), db)
        assert exc.value.status_code == 400

    def test_valid_ocf_epub_accepted(self, ebooks_root, db):
        from app.services import library_storage
        payload = _epub_bytes_raw([("META-INF/container.xml", "<container/>")])
        rel, _ = library_storage.save_ebook_file(7, _upload("book.epub", payload), db)
        assert rel.endswith(".epub")


class TestI3ExtensionFromSniffedContent:
    """I3: the extension used for storage/serving must come from sniffing
    the actual bytes, not the client-supplied filename; and a rejected
    filename must never be echoed back raw in the error detail."""

    def test_trailing_space_extension_rejected_without_echoing_filename(self, ebooks_root, db):
        from app.services import library_storage
        with pytest.raises(HTTPException) as exc:
            library_storage.save_ebook_file(7, _upload("a.pdf ", PDF_BYTES), db)
        assert exc.value.status_code == 400
        detail = str(exc.value.detail)
        assert "a.pdf" not in detail  # raw client filename (or any prefix of it) never echoed

    def test_trailing_dot_extension_rejected_without_echoing_filename(self, ebooks_root, db):
        from app.services import library_storage
        with pytest.raises(HTTPException) as exc:
            library_storage.save_ebook_file(7, _upload("a.pdf.", PDF_BYTES), db)
        assert exc.value.status_code == 400
        detail = str(exc.value.detail)
        assert "a.pdf" not in detail

    def test_content_decides_extension_not_client_filename(self, ebooks_root, db):
        # Client names it .epub but the allowlist pre-check passes (epub is
        # allowed); the actual bytes are a PDF, so sniffing must reject it
        # as a content/extension mismatch rather than trusting the filename.
        from app.services import library_storage
        with pytest.raises(HTTPException) as exc:
            library_storage.save_ebook_file(7, _upload("disguised.epub", PDF_BYTES), db)
        assert exc.value.status_code == 400

    def test_stored_extension_matches_sniffed_content_not_filename_case(self, ebooks_root, db):
        # A PDF whose filename claims .pdf in a case-mangled way must still
        # be stored under the extension derived from sniffing, and the
        # allowlist pre-check must key off the client name only to gate
        # entry, never to choose the final on-disk extension.
        from app.services import library_storage
        rel, _ = library_storage.save_ebook_file(7, _upload("Report.PDF", PDF_BYTES), db)
        assert rel.endswith(".pdf")  # sniffed/normalized, not echoed as "PDF"


class TestI4EbooksRootIsAbsoluteAndCwdIndependent:
    """I4: EBOOKS_ROOT must be an absolute path anchored to the backend
    package, not CWD-relative — the module attribute itself (before any
    test monkeypatches it) must already resolve this way."""

    def test_default_root_is_absolute_regardless_of_cwd(self):
        import importlib
        import os

        from app.services import library_storage
        importlib.reload(library_storage)

        original_cwd = os.getcwd()
        try:
            os.chdir(os.path.dirname(original_cwd) or original_cwd)
            assert library_storage.EBOOKS_ROOT.is_absolute()
            root_from_elsewhere = library_storage.EBOOKS_ROOT
        finally:
            os.chdir(original_cwd)
            importlib.reload(library_storage)

        assert root_from_elsewhere.is_absolute()
        assert root_from_elsewhere.name == "ebooks"

    def test_gitignore_covers_backend_ebooks(self):
        gitignore = Path(__file__).resolve().parents[2] / ".gitignore"
        text = gitignore.read_text(encoding="utf-8")
        assert "backend/ebooks" in text


class TestMinorsGuardsAndStatusCodes:
    """M2 (allowed=set() must not silently fall back to the default
    allowlist), M3 (413 uses HTTP_413_CONTENT_TOO_LARGE), M4 (a malformed
    owner_id is a clean 400, never an unhandled 500)."""

    def test_empty_allowed_set_rejects_everything(self, ebooks_root, db):
        # `allowed=set()` is a deliberate "nothing is allowed" — must not
        # be treated the same as "not provided" (falsy `or` fallback bug).
        from app.services import library_storage
        with pytest.raises(HTTPException) as exc:
            library_storage.save_ebook_file(7, _upload("ok.pdf", PDF_BYTES), db, allowed=set())
        assert exc.value.status_code == 400

    def test_non_integer_owner_id_is_400_not_500(self, ebooks_root, db):
        from app.services import library_storage
        with pytest.raises(HTTPException) as exc:
            library_storage.save_ebook_file("not-an-id", _upload("ok.pdf", PDF_BYTES), db)
        assert exc.value.status_code == 400

    def test_oversize_uses_413_content_too_large_status(self, ebooks_root, db, monkeypatch):
        from fastapi import status as fastapi_status

        from app.services import library_storage
        monkeypatch.setattr(library_storage, "MAX_FILE_BYTES", 16)
        with pytest.raises(HTTPException) as exc:
            library_storage.save_ebook_file(7, _upload("big.pdf", PDF_BYTES), db)
        assert exc.value.status_code == 413

    def test_quota_check_always_runs_even_when_owner_has_zero_usage(self, ebooks_root, db, monkeypatch):
        # The cap check is unconditional now (no `if db is not None` skip
        # branch) — prove it actually executes on the happy path too, by
        # making owner_total_bytes explode if it's ever NOT called and by
        # setting a cap so tight that a real call must reject the 2nd file.
        from app.services import library_storage
        monkeypatch.setattr(library_storage, "MAX_OWNER_TOTAL_BYTES", len(PDF_BYTES))
        calls = []
        real_owner_total_bytes = library_storage.owner_total_bytes

        def _spy(db_arg, owner_id):
            calls.append(owner_id)
            return real_owner_total_bytes(db_arg, owner_id)

        monkeypatch.setattr(library_storage, "owner_total_bytes", _spy)
        library_storage.save_ebook_file(7, _upload("a.pdf", PDF_BYTES), db)
        assert calls == [7]  # the quota check ran on the very first call


# ============================================================================
# Round 3: scoped re-review residuals (New-1, New-2, New-3)
# ============================================================================


def _epub_with_declared_size(entries_declared_total: int, *, real_padding: bytes = b"") -> bytes:
    """Build a real, valid-OCF zip whose 'mimetype' entry is genuine, plus
    one additional STORED entry whose declared uncompressed size is patched
    (via struct, same technique as _encrypted_zip_bytes/the huge-mimetype
    test above) to `entries_declared_total` while its ACTUAL on-disk bytes
    stay tiny (`real_padding`, default empty). This lets tests exercise the
    declared-size cap and the compression-ratio guard without ever writing
    real multi-hundred-MB payloads."""
    import struct

    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        zf.writestr(zipfile.ZipInfo("mimetype"), b"application/epub+zip",
                    zipfile.ZIP_STORED)
        zf.writestr("META-INF/container.xml", "<container/>")
        zf.writestr(zipfile.ZipInfo("big.bin"), real_padding, zipfile.ZIP_STORED)
    data = bytearray(buf.getvalue())

    lfh_sig = b"PK\x03\x04"
    cdh_sig = b"PK\x01\x02"

    # Find the LOCAL file header for "big.bin" specifically (not mimetype's,
    # which shares the same signature) by locating its filename bytes and
    # walking back to the header start (30-byte fixed header immediately
    # precedes the filename).
    name_idx = data.find(b"big.bin")
    assert name_idx != -1
    lfh_idx = data.rfind(lfh_sig, 0, name_idx)
    assert lfh_idx != -1 and name_idx - lfh_idx == 30
    struct.pack_into("<I", data, lfh_idx + 22, entries_declared_total)  # uncomp_size

    # Central directory entry for "big.bin": find its filename occurrence
    # inside a central-directory record (46-byte fixed header precedes it).
    search_from = 0
    while True:
        cdh_idx = data.find(cdh_sig, search_from)
        assert cdh_idx != -1, "big.bin central directory record not found"
        cdh_name_idx = cdh_idx + 46
        name_len = struct.unpack_from("<H", data, cdh_idx + 28)[0]
        if data[cdh_name_idx:cdh_name_idx + name_len] == b"big.bin":
            struct.pack_into("<I", data, cdh_idx + 24, entries_declared_total)  # uncomp_size
            break
        search_from = cdh_idx + 1

    return bytes(data)


class TestNew1EpubSizeCapsAndCompressionRatio:
    """New-1 (Important, Round 3): MAX_EPUB_UNCOMPRESSED = 1 GiB was too
    loose (a ~1MB file declaring ~1GiB was accepted, 1029x ratio) and
    MAX_EPUB_ENTRIES too high vs. h5p_service's posture. Fix: lower both to
    match h5p_service (300 MiB / 2000 entries) AND add a compression-ratio
    guard (declared_total > MAX_EPUB_RATIO x compressed_size => reject),
    applied only when declared_total > 10 MiB so tiny legitimate epubs are
    never penalized."""

    def test_caps_lowered_to_h5p_posture(self):
        from app.services import library_storage
        assert library_storage.MAX_EPUB_UNCOMPRESSED == 300 * 1024 * 1024
        assert library_storage.MAX_EPUB_ENTRIES == 2000

    def test_gigabyte_declared_on_tiny_epub_rejected(self, ebooks_root, db):
        # The exact New-1 exploit payload: ~1MB real epub, one entry
        # declaring ~1GiB uncompressed (1029x ratio AND over the absolute cap).
        from app.services import library_storage
        payload = _epub_with_declared_size(1_072_693_248, real_padding=b"0" * 1_040_000)
        with pytest.raises(HTTPException) as exc:
            library_storage.save_ebook_file(7, _upload("bomb.epub", payload), db)
        assert exc.value.status_code == 400
        leftovers = list(ebooks_root.rglob("*")) if ebooks_root.exists() else []
        assert not [p for p in leftovers if p.is_file()]

    def test_tiny_zip_declaring_200mb_rejected(self, ebooks_root, db):
        # The original C2b payload: near-empty zip declaring 200MB for one
        # entry. Over both the absolute cap (300MiB > 200MB doesn't trip the
        # absolute cap by itself, but the ratio guard must catch this: a
        # near-zero compressed size against a 200MB declared size is an
        # extreme ratio) and the ratio guard.
        from app.services import library_storage
        payload = _epub_with_declared_size(200 * 1024 * 1024, real_padding=b"")
        with pytest.raises(HTTPException) as exc:
            library_storage.save_ebook_file(7, _upload("tinybomb.epub", payload), db)
        assert exc.value.status_code == 400
        leftovers = list(ebooks_root.rglob("*")) if ebooks_root.exists() else []
        assert not [p for p in leftovers if p.is_file()]

    def test_normal_epub_still_accepted(self, ebooks_root, db):
        # A legitimately-sized epub (~2MB declared content, ~500KB actual
        # compressed-on-disk) must NOT be penalized by either cap or the
        # ratio guard.
        from app.services import library_storage
        real_bytes = os.urandom(500_000)  # incompressible padding so the
        # zip's on-disk/compressed size stays close to the real byte count
        payload = _epub_with_declared_size(2 * 1024 * 1024, real_padding=real_bytes)
        rel, _ = library_storage.save_ebook_file(7, _upload("normal.epub", payload), db)
        assert rel.endswith(".epub")

    def test_moderate_ratio_epub_accepted(self, ebooks_root, db):
        # 250MB declared / ~50MB compressed = ratio 5, well under the 100x
        # threshold, and under the 300MiB absolute cap — must be accepted.
        # Constructed via declared-size patching (never real 250MB data):
        # the actual on-disk/compressed size is what the ratio guard
        # measures, so we pad with real (incompressible) bytes sized to
        # land the *compressed* size around ~50MB while the *declared*
        # uncompressed size is patched to 250MB.
        from app.services import library_storage
        real_bytes = os.urandom(50 * 1024 * 1024)
        payload = _epub_with_declared_size(250 * 1024 * 1024, real_padding=real_bytes)
        rel, _ = library_storage.save_ebook_file(7, _upload("moderate.epub", payload), db)
        assert rel.endswith(".epub")


class TestNew2NonStringFilenameRejected:
    """New-2 (Minor, Round 3): a non-str filename (e.g. bytes) must be a
    clean 400 ("Invalid filename"), never an escaping TypeError — same
    posture as the M4 owner_id guard."""

    def test_bytes_filename_rejected_cleanly(self, ebooks_root, db):
        from app.services import library_storage
        upload = UploadFile(filename=b"evil.pdf", file=io.BytesIO(PDF_BYTES))  # type: ignore[arg-type]
        with pytest.raises(HTTPException) as exc:
            library_storage.save_ebook_file(7, upload, db)
        assert exc.value.status_code == 400


class TestNew3StrictOwnerIdCoercion:
    """New-3 (Minor, Round 3): owner_id coercion was too permissive
    (True -> 1, 1.9 -> 1, b"7"/"7" -> 7). Only a real int (excluding bool)
    or a pure-digit str may be accepted; everything else is a clean 400."""

    def test_bool_owner_id_rejected(self, ebooks_root, db):
        from app.services import library_storage
        with pytest.raises(HTTPException) as exc:
            library_storage.save_ebook_file(True, _upload("ok.pdf", PDF_BYTES), db)
        assert exc.value.status_code == 400

    def test_float_owner_id_rejected(self, ebooks_root, db):
        from app.services import library_storage
        with pytest.raises(HTTPException) as exc:
            library_storage.save_ebook_file(1.9, _upload("ok.pdf", PDF_BYTES), db)
        assert exc.value.status_code == 400

    def test_bytes_owner_id_rejected(self, ebooks_root, db):
        from app.services import library_storage
        with pytest.raises(HTTPException) as exc:
            library_storage.save_ebook_file(b"7", _upload("ok.pdf", PDF_BYTES), db)
        assert exc.value.status_code == 400


# ============================================================================
# Task 3: instructor CRUD + ownership
# ============================================================================


def _create_payload(**over):
    payload = {
        "title": "Tamil Grammar Guide",
        "description": "A concise guide.",
        "category": "guide",
        "price_inr": 299,
        "concept_tags": ["grammar", "tamil"],
    }
    payload.update(over)
    return payload


class TestInstructorCrud:
    def test_create_draft_generates_slug(self, client, db, make_user, auth_headers):
        owner = _make_approved_instructor(db, make_user, "crud-a@lib.com")
        r = client.post("/api/v1/library", json=_create_payload(),
                        headers=auth_headers(owner.user_email))
        assert r.status_code == 200, r.text
        body = r.json()
        assert body["status"] == "draft"
        assert body["slug"].startswith("tamil-grammar-guide-")
        assert body["effective_price_inr"] == 299
        assert "file_path" not in body and "sample_path" not in body  # NEVER leaked

    def test_student_cannot_create(self, client, db, make_user, auth_headers):
        student = make_user(role="student")
        r = client.post("/api/v1/library", json=_create_payload(),
                        headers=auth_headers(student.user_email))
        assert r.status_code == 403

    @pytest.mark.parametrize("mutate", [
        {"category": "magazine"},                        # not in enum
        {"discount_price_inr": 299},                     # not < price
        {"discount_price_inr": 400},                     # > price
        {"concept_tags": [f"t{i}" for i in range(11)]},  # >10 tags
        {"concept_tags": ["x" * 51]},                    # tag >50 chars
        {"title": ""},                                   # empty title
        {"price_inr": -5},                               # negative price
        {"description": "d" * 5001},                     # >5000
    ])
    def test_metadata_validation(self, client, db, make_user, auth_headers, mutate):
        owner = _make_approved_instructor(db, make_user, "crud-b@lib.com")
        r = client.post("/api/v1/library", json=_create_payload(**mutate),
                        headers=auth_headers(owner.user_email))
        assert r.status_code == 422, r.text

    def test_cross_owner_blocked_everywhere(self, client, db, make_user,
                                            auth_headers, ebooks_root):
        a = _make_approved_instructor(db, make_user, "crud-c@lib.com")
        b = _make_approved_instructor(db, make_user, "crud-d@lib.com")
        ebook = _make_ebook(db, a)
        hb = auth_headers(b.user_email)
        assert client.put(f"/api/v1/library/{ebook.id}", json={"title": "hijack"},
                          headers=hb).status_code == 403
        assert client.post(f"/api/v1/library/{ebook.id}/file",
                           files={"file": ("x.pdf", PDF_BYTES, "application/pdf")},
                           headers=hb).status_code == 403
        assert client.post(f"/api/v1/library/{ebook.id}/publish",
                           headers=hb).status_code == 403
        assert client.post(f"/api/v1/library/{ebook.id}/unpublish",
                           headers=hb).status_code == 403
        assert client.delete(f"/api/v1/library/{ebook.id}",
                             headers=hb).status_code == 403
        assert client.get(f"/api/v1/library/{ebook.id}/sales",
                          headers=hb).status_code == 403

    def test_student_blocked_everywhere(self, client, db, make_user, auth_headers,
                                        ebooks_root):
        owner = _make_approved_instructor(db, make_user, "crud-s1@lib.com")
        ebook = _make_ebook(db, owner)
        student = make_user(role="student")
        hs = auth_headers(student.user_email)
        assert client.put(f"/api/v1/library/{ebook.id}", json={"title": "hijack"},
                          headers=hs).status_code == 403
        assert client.post(f"/api/v1/library/{ebook.id}/file",
                           files={"file": ("x.pdf", PDF_BYTES, "application/pdf")},
                           headers=hs).status_code == 403
        assert client.post(f"/api/v1/library/{ebook.id}/publish",
                           headers=hs).status_code == 403
        assert client.get("/api/v1/library/mine", headers=hs).status_code == 403
        assert client.delete(f"/api/v1/library/{ebook.id}",
                             headers=hs).status_code == 403
        assert client.get(f"/api/v1/library/{ebook.id}/sales",
                          headers=hs).status_code == 403

    def test_mine_lists_only_own(self, client, db, make_user, auth_headers):
        a = _make_approved_instructor(db, make_user, "crud-e@lib.com")
        b = _make_approved_instructor(db, make_user, "crud-f@lib.com")
        _make_ebook(db, a, title="A Book")
        _make_ebook(db, b, title="B Book")
        r = client.get("/api/v1/library/mine", headers=auth_headers(a.user_email))
        assert r.status_code == 200
        assert [e["title"] for e in r.json()["ebooks"]] == ["A Book"]

    def test_mine_admin_sees_all(self, client, db, make_user, auth_headers):
        a = _make_approved_instructor(db, make_user, "crud-e2@lib.com")
        b = _make_approved_instructor(db, make_user, "crud-f2@lib.com")
        _make_ebook(db, a, title="A Book")
        _make_ebook(db, b, title="B Book")
        admin = make_user(role="admin", email="crud-admin1@lib.com")
        headers = _admin_headers(client, db, admin)
        r = client.get("/api/v1/library/mine", headers=headers)
        assert r.status_code == 200
        titles = {e["title"] for e in r.json()["ebooks"]}
        assert titles == {"A Book", "B Book"}

    def test_get_own_vs_other_instructor_via_update(self, client, db, make_user,
                                                     auth_headers):
        """No direct GET /{id} exists yet (Task 4 adds the public/detail GET);
        ownership on reads-that-matter today is exercised via PUT (owner
        succeeds, other-instructor 403, student 403 — see
        test_cross_owner_blocked_everywhere / test_student_blocked_everywhere)."""
        owner = _make_approved_instructor(db, make_user, "crud-own@lib.com")
        other = _make_approved_instructor(db, make_user, "crud-other@lib.com")
        ebook = _make_ebook(db, owner)
        r = client.put(f"/api/v1/library/{ebook.id}", json={"title": "Updated"},
                       headers=auth_headers(owner.user_email))
        assert r.status_code == 200
        assert r.json()["title"] == "Updated"
        r2 = client.put(f"/api/v1/library/{ebook.id}", json={"title": "hijack"},
                        headers=auth_headers(other.user_email))
        assert r2.status_code == 403

    def test_update_revalidates_discount_against_merged_row(self, client, db,
                                                             make_user, auth_headers):
        owner = _make_approved_instructor(db, make_user, "crud-k@lib.com")
        ebook = _make_ebook(db, owner, price=500, discount=400)
        h = auth_headers(owner.user_email)
        # Lowering price below the KEPT discount must fail the merged check.
        r = client.put(f"/api/v1/library/{ebook.id}", json={"price_inr": 300},
                       headers=h)
        assert r.status_code == 422

    def test_upload_then_publish_flow(self, client, db, make_user, auth_headers,
                                      ebooks_root):
        owner = _make_approved_instructor(db, make_user, "crud-g@lib.com")
        h = auth_headers(owner.user_email)
        ebook_id = client.post("/api/v1/library", json=_create_payload(),
                               headers=h).json()["id"]
        # publish before file → 400
        r = client.post(f"/api/v1/library/{ebook_id}/publish", headers=h)
        assert r.status_code == 400
        assert "file" in r.json()["detail"].lower()
        # upload, then publish works
        r = client.post(f"/api/v1/library/{ebook_id}/file",
                        files={"file": ("g.pdf", PDF_BYTES, "application/pdf")},
                        headers=h)
        assert r.status_code == 200, r.text
        assert r.json()["has_file"] is True
        assert client.post(f"/api/v1/library/{ebook_id}/publish",
                           headers=h).json()["status"] == "published"
        # sample rejects epub
        r = client.post(f"/api/v1/library/{ebook_id}/sample",
                        files={"file": ("s.epub", _epub_bytes(),
                                        "application/epub+zip")}, headers=h)
        assert r.status_code == 400
        # unpublish always allowed
        assert client.post(f"/api/v1/library/{ebook_id}/unpublish",
                           headers=h).json()["status"] == "draft"

    def test_upload_replaces_old_file_on_disk(self, client, db, make_user,
                                              auth_headers, ebooks_root):
        from app.services import library_storage
        owner = _make_approved_instructor(db, make_user, "crud-repl@lib.com")
        h = auth_headers(owner.user_email)
        ebook_id = client.post("/api/v1/library", json=_create_payload(),
                               headers=h).json()["id"]
        r1 = client.post(f"/api/v1/library/{ebook_id}/file",
                         files={"file": ("first.pdf", PDF_BYTES, "application/pdf")},
                         headers=h)
        assert r1.status_code == 200
        row = db.query(Ebook).filter(Ebook.id == ebook_id).first()
        first_path = library_storage.resolve_ebook_path(row.file_path)
        assert first_path.is_file()

        r2 = client.post(f"/api/v1/library/{ebook_id}/file",
                         files={"file": ("second.pdf", PDF_BYTES, "application/pdf")},
                         headers=h)
        assert r2.status_code == 200
        db.refresh(row)
        assert row.file_path != first_path.relative_to(
            library_storage.EBOOKS_ROOT).as_posix()
        assert not first_path.is_file()  # old blob removed, no orphan
        assert library_storage.resolve_ebook_path(row.file_path).is_file()

    def test_upload_oversize_rejected_no_row_change(self, client, db, make_user,
                                                     auth_headers, ebooks_root,
                                                     monkeypatch):
        from app.services import library_storage
        monkeypatch.setattr(library_storage, "MAX_FILE_BYTES", 8)
        owner = _make_approved_instructor(db, make_user, "crud-big@lib.com")
        h = auth_headers(owner.user_email)
        ebook_id = client.post("/api/v1/library", json=_create_payload(),
                               headers=h).json()["id"]
        r = client.post(f"/api/v1/library/{ebook_id}/file",
                        files={"file": ("g.pdf", PDF_BYTES, "application/pdf")},
                        headers=h)
        assert r.status_code == 413
        row = db.query(Ebook).filter(Ebook.id == ebook_id).first()
        assert row.file_path is None
        assert row.file_size_bytes == 0

    def test_upload_invalid_type_rejected_no_row_change(self, client, db, make_user,
                                                         auth_headers, ebooks_root):
        owner = _make_approved_instructor(db, make_user, "crud-bad@lib.com")
        h = auth_headers(owner.user_email)
        ebook_id = client.post("/api/v1/library", json=_create_payload(),
                               headers=h).json()["id"]
        r = client.post(f"/api/v1/library/{ebook_id}/file",
                        files={"file": ("notes.txt", PDF_BYTES, "text/plain")},
                        headers=h)
        assert r.status_code == 400
        row = db.query(Ebook).filter(Ebook.id == ebook_id).first()
        assert row.file_path is None

    def test_delete_409_with_grants(self, client, db, make_user, auth_headers,
                                    ebooks_root):
        owner = _make_approved_instructor(db, make_user, "crud-h@lib.com")
        student = make_user(role="student")
        ebook = _make_ebook(db, owner, status="published")
        _grant(db, ebook, student)
        r = client.delete(f"/api/v1/library/{ebook.id}",
                          headers=auth_headers(owner.user_email))
        assert r.status_code == 409
        assert db.query(Ebook).filter(Ebook.id == ebook.id).first() is not None

    def test_delete_without_grants_removes_row(self, client, db, make_user,
                                               auth_headers, ebooks_root):
        owner = _make_approved_instructor(db, make_user, "crud-i@lib.com")
        ebook = _make_ebook(db, owner)
        r = client.delete(f"/api/v1/library/{ebook.id}",
                          headers=auth_headers(owner.user_email))
        assert r.status_code == 200
        assert db.query(Ebook).filter(Ebook.id == ebook.id).first() is None

    def test_delete_removes_files_from_disk(self, client, db, make_user,
                                            auth_headers, ebooks_root):
        from app.services import library_storage
        owner = _make_approved_instructor(db, make_user, "crud-delfile@lib.com")
        h = auth_headers(owner.user_email)
        ebook_id = client.post("/api/v1/library", json=_create_payload(),
                               headers=h).json()["id"]
        client.post(f"/api/v1/library/{ebook_id}/file",
                   files={"file": ("g.pdf", PDF_BYTES, "application/pdf")}, headers=h)
        row = db.query(Ebook).filter(Ebook.id == ebook_id).first()
        stored = library_storage.resolve_ebook_path(row.file_path)
        assert stored.is_file()
        r = client.delete(f"/api/v1/library/{ebook_id}", headers=h)
        assert r.status_code == 200
        assert not stored.is_file()

    def test_delete_tolerates_missing_file_on_disk(self, client, db, make_user,
                                                    auth_headers, ebooks_root):
        """delete removes the DB row then the file; a file already missing
        from disk (ops cleanup, manual removal) must not turn delete into a
        500 — the file removal is best-effort."""
        owner = _make_approved_instructor(db, make_user, "crud-nofile@lib.com")
        ebook = _make_ebook(db, owner, file_path="does/not/exist.pdf")
        r = client.delete(f"/api/v1/library/{ebook.id}",
                          headers=auth_headers(owner.user_email))
        assert r.status_code == 200
        assert db.query(Ebook).filter(Ebook.id == ebook.id).first() is None

    def test_sales_panel_shape_no_emails(self, client, db, make_user, auth_headers):
        owner = _make_approved_instructor(db, make_user, "crud-j@lib.com")
        student = make_user(role="student")
        ebook = _make_ebook(db, owner, status="published")
        _grant(db, ebook, student)
        r = client.get(f"/api/v1/library/{ebook.id}/sales",
                       headers=auth_headers(owner.user_email))
        assert r.status_code == 200
        body = r.json()
        assert body["count"] == 1
        assert body["gross_inr"] == 0.0  # free/hand grant: no OrderItem money
        assert body["buyers"][0]["display_name"] == student.display_name
        import json as _json
        assert "user_email" not in _json.dumps(body)  # spec §4: no buyer emails

    def test_slug_tamil_title_falls_back_to_ebook_id(self, client, db, make_user,
                                                      auth_headers):
        owner = _make_approved_instructor(db, make_user, "crud-tamil@lib.com")
        r = client.post("/api/v1/library",
                        json=_create_payload(title="தமிழ்"),
                        headers=auth_headers(owner.user_email))
        assert r.status_code == 200, r.text
        body = r.json()
        assert body["slug"] == f"ebook-{body['id']}"

    def test_slug_update_regenerates_on_title_change(self, client, db, make_user,
                                                      auth_headers):
        owner = _make_approved_instructor(db, make_user, "crud-slug2@lib.com")
        ebook = _make_ebook(db, owner, title="Original Title")
        h = auth_headers(owner.user_email)
        r = client.put(f"/api/v1/library/{ebook.id}",
                       json={"title": "Brand New Title"}, headers=h)
        assert r.status_code == 200
        assert r.json()["slug"] == f"brand-new-title-{ebook.id}"


# ============================================================================
# Task 4: public store + caching + download/sample gates
# ============================================================================


class TestPublicStore:
    def test_list_filters(self, client, db, make_user, course):
        owner = _make_approved_instructor(db, make_user, "store-a@lib.com")
        _make_ebook(db, owner, title="Algebra Book", category="book",
                    status="published", tags=["algebra"])
        _make_ebook(db, owner, title="Algebra Notes", category="lecture_notes",
                    status="published", course_id=course.id)
        _make_ebook(db, owner, title="Hidden Draft", status="draft")

        assert client.get("/api/v1/library").json()["count"] == 2  # drafts never listed
        r = client.get("/api/v1/library", params={"category": "book"})
        assert [e["title"] for e in r.json()["ebooks"]] == ["Algebra Book"]
        r = client.get("/api/v1/library", params={"q": "notes"})
        assert [e["title"] for e in r.json()["ebooks"]] == ["Algebra Notes"]
        r = client.get("/api/v1/library", params={"course_id": course.id})
        assert r.json()["count"] == 1
        r = client.get("/api/v1/library", params={"tag": "Algebra"})  # case-insensitive
        assert [e["title"] for e in r.json()["ebooks"]] == ["Algebra Book"]

    def test_list_hides_draft_even_from_its_owner(self, client, db, make_user,
                                                  auth_headers):
        """The PUBLIC route is status-scoped, not user-scoped: an owner sees
        their own drafts on /mine, never in the store listing."""
        owner = _make_approved_instructor(db, make_user, "store-owner@lib.com")
        _make_ebook(db, owner, title="Owner Draft", status="draft")
        r = client.get("/api/v1/library", headers=auth_headers(owner.user_email))
        assert r.status_code == 200
        assert r.json()["count"] == 0

    def test_list_never_leaks_paths_or_emails(self, client, db, make_user):
        owner = _make_approved_instructor(db, make_user, "store-leak@lib.com")
        _make_ebook(db, owner, status="published", file_path="1/secret.pdf",
                    sample_path="1/sample.pdf")
        r = client.get("/api/v1/library")
        assert r.status_code == 200
        raw = r.text
        assert "file_path" not in raw and "sample_path" not in raw
        assert "secret.pdf" not in raw
        assert owner.user_email not in raw
        item = r.json()["ebooks"][0]
        assert item["has_file"] is True and item["has_sample"] is True

    def test_detail_owned_flag_only_when_authed(self, client, db, make_user,
                                                auth_headers):
        owner = _make_approved_instructor(db, make_user, "store-b@lib.com")
        student = make_user(role="student")
        ebook = _make_ebook(db, owner, status="published")
        _grant(db, ebook, student)

        anon = client.get(f"/api/v1/library/{ebook.slug}")
        assert anon.status_code == 200
        assert "owned" not in anon.json()          # anon body is user-independent

        authed = client.get(f"/api/v1/library/{ebook.slug}",
                            headers=auth_headers(student.user_email))
        assert authed.json()["owned"] is True

        other = make_user(role="student", email="store-nobody@lib.com")
        r = client.get(f"/api/v1/library/{ebook.slug}",
                       headers=auth_headers(other.user_email))
        assert r.json()["owned"] is False

    def test_detail_404_for_draft(self, client, db, make_user):
        owner = _make_approved_instructor(db, make_user, "store-c@lib.com")
        ebook = _make_ebook(db, owner, status="draft")
        assert client.get(f"/api/v1/library/{ebook.slug}").status_code == 404

    def test_detail_404_for_draft_to_student(self, client, db, make_user,
                                             auth_headers):
        owner = _make_approved_instructor(db, make_user, "store-c2@lib.com")
        student = make_user(role="student", email="store-c2-stu@lib.com")
        ebook = _make_ebook(db, owner, status="draft")
        r = client.get(f"/api/v1/library/{ebook.slug}",
                       headers=auth_headers(student.user_email))
        assert r.status_code == 404

    def test_detail_slug_lookup_is_exact_no_traversal(self, client, db, make_user):
        """Slugs are matched exactly - no LIKE, no path semantics. A traversal
        payload is just a slug that does not exist."""
        owner = _make_approved_instructor(db, make_user, "store-trav@lib.com")
        ebook = _make_ebook(db, owner, title="Real Book", status="published")
        for probe in ["..", "../../etc/passwd", f"%{ebook.slug}%",
                      f"{ebook.slug}x", ebook.slug.upper() + "zz"]:
            r = client.get(f"/api/v1/library/{probe}")
            assert r.status_code == 404, probe

    def test_me_lists_grants(self, client, db, make_user, auth_headers):
        owner = _make_approved_instructor(db, make_user, "store-d@lib.com")
        student = make_user(role="student")
        with_file = _make_ebook(db, owner, title="Has File", status="published",
                                file_path="1/abc.pdf")
        _grant(db, with_file, student)
        r = client.get("/api/v1/library/me", headers=auth_headers(student.user_email))
        assert r.status_code == 200
        item = r.json()["items"][0]
        assert item["title"] == "Has File"
        assert item["downloadable"] is True
        assert "granted_at" in item
        assert client.get("/api/v1/library/me").status_code in (401, 403)  # authed only

    def test_me_includes_unpublished_grants_and_hides_others(self, client, db,
                                                             make_user, auth_headers):
        owner = _make_approved_instructor(db, make_user, "store-e@lib.com")
        student = make_user(role="student", email="store-e-stu@lib.com")
        stranger = make_user(role="student", email="store-e-other@lib.com")
        mine = _make_ebook(db, owner, title="Mine", status="draft",
                           file_path="1/mine.pdf")
        theirs = _make_ebook(db, owner, title="Theirs", status="published",
                             file_path="1/theirs.pdf")
        _grant(db, mine, student)
        _grant(db, theirs, stranger)
        r = client.get("/api/v1/library/me", headers=auth_headers(student.user_email))
        assert [i["title"] for i in r.json()["items"]] == ["Mine"]
        assert "file_path" not in r.text


class TestCacheHeaders:
    def test_list_anon_cacheable_authed_private(self, client, db, make_user,
                                                auth_headers):
        student = make_user(role="student")
        anon = client.get("/api/v1/library")
        assert anon.headers["Cache-Control"] == \
            "public, s-maxage=300, stale-while-revalidate=600"
        assert anon.headers["Vary"] == "Authorization"
        authed = client.get("/api/v1/library",
                            headers=auth_headers(student.user_email))
        assert authed.headers["Cache-Control"] == "private, no-store"

    def test_detail_anon_cacheable_authed_private(self, client, db, make_user,
                                                  auth_headers):
        owner = _make_approved_instructor(db, make_user, "cache-a@lib.com")
        student = make_user(role="student")
        ebook = _make_ebook(db, owner, status="published")
        anon = client.get(f"/api/v1/library/{ebook.slug}")
        assert anon.headers["Cache-Control"] == \
            "public, s-maxage=60, stale-while-revalidate=600"
        authed = client.get(f"/api/v1/library/{ebook.slug}",
                            headers=auth_headers(student.user_email))
        assert authed.headers["Cache-Control"] == "private, no-store"

    def test_me_never_edge_cached(self, client, db, make_user, auth_headers):
        student = make_user(role="student")
        r = client.get("/api/v1/library/me", headers=auth_headers(student.user_email))
        assert "s-maxage" not in r.headers.get("Cache-Control", "")


class TestDownloadGates:
    def _published_with_file(self, client, db, make_user, auth_headers, email,
                             sample=False):
        owner = _make_approved_instructor(db, make_user, email)
        h = auth_headers(owner.user_email)
        ebook_id = client.post("/api/v1/library", json=_create_payload(),
                               headers=h).json()["id"]
        client.post(f"/api/v1/library/{ebook_id}/file",
                    files={"file": ("f.pdf", PDF_BYTES, "application/pdf")}, headers=h)
        if sample:
            client.post(f"/api/v1/library/{ebook_id}/sample",
                        files={"file": ("s.pdf", PDF_BYTES, "application/pdf")},
                        headers=h)
        client.post(f"/api/v1/library/{ebook_id}/publish", headers=h)
        db.expire_all()
        return db.query(Ebook).filter(Ebook.id == ebook_id).one(), h

    def test_no_grant_403_granted_200_streams_bytes(self, client, db, make_user,
                                                    auth_headers, ebooks_root):
        ebook, _ = self._published_with_file(client, db, make_user, auth_headers,
                                             "dl-a@lib.com")
        student = make_user(role="student")
        hs = auth_headers(student.user_email)
        assert client.get(f"/api/v1/library/{ebook.id}/download",
                          headers=hs).status_code == 403
        _grant(db, ebook, student)
        r = client.get(f"/api/v1/library/{ebook.id}/download", headers=hs)
        assert r.status_code == 200
        assert r.content == PDF_BYTES                     # actual bytes, not a redirect
        assert r.headers["content-type"].startswith("application/pdf")
        assert "attachment" in r.headers["content-disposition"]
        assert client.get(f"/api/v1/library/{ebook.id}/download").status_code \
            in (401, 403)                                  # anon never downloads

    def test_download_never_public_cached_and_never_leaks_path(
            self, client, db, make_user, auth_headers, ebooks_root):
        ebook, _ = self._published_with_file(client, db, make_user, auth_headers,
                                             "dl-cache@lib.com")
        student = make_user(role="student", email="dl-cache-stu@lib.com")
        _grant(db, ebook, student)
        r = client.get(f"/api/v1/library/{ebook.id}/download",
                       headers=auth_headers(student.user_email))
        assert r.status_code == 200
        cc = r.headers.get("Cache-Control", "")
        assert "s-maxage" not in cc and "public" not in cc
        # the stored uuid filename / owner dir must never appear in any header
        joined = " ".join(f"{k}: {v}" for k, v in r.headers.items())
        assert Path(ebook.file_path).name not in joined
        assert str(ebooks_root) not in joined
        assert ebook.slug in r.headers["content-disposition"]

    def test_other_users_grant_does_not_help(self, client, db, make_user,
                                             auth_headers, ebooks_root):
        ebook, _ = self._published_with_file(client, db, make_user, auth_headers,
                                             "dl-cross@lib.com")
        buyer = make_user(role="student", email="dl-cross-buyer@lib.com")
        thief = make_user(role="student", email="dl-cross-thief@lib.com")
        _grant(db, ebook, buyer)
        r = client.get(f"/api/v1/library/{ebook.id}/download",
                       headers=auth_headers(thief.user_email))
        assert r.status_code == 403

    def test_owner_and_admin_download_without_grant(self, client, db, make_user,
                                                    auth_headers, ebooks_root):
        ebook, owner_h = self._published_with_file(client, db, make_user,
                                                   auth_headers, "dl-b@lib.com")
        assert client.get(f"/api/v1/library/{ebook.id}/download",
                          headers=owner_h).status_code == 200
        admin = make_user(role="admin", email="dl-b-admin@lib.com")
        admin_h = _admin_headers(client, db, admin)
        assert client.get(f"/api/v1/library/{ebook.id}/download",
                          headers=admin_h).status_code == 200

    def test_draft_download_404_to_non_owner(self, client, db, make_user,
                                             auth_headers, ebooks_root):
        ebook, owner_h = self._published_with_file(client, db, make_user,
                                                   auth_headers, "dl-c@lib.com")
        client.post(f"/api/v1/library/{ebook.id}/unpublish", headers=owner_h)
        stranger = make_user(role="student", email="dl-stranger@lib.com")
        r = client.get(f"/api/v1/library/{ebook.id}/download",
                       headers=auth_headers(stranger.user_email))
        assert r.status_code == 404  # drafts do not leak existence to non-owners

    def test_owner_and_admin_download_draft(self, client, db, make_user,
                                            auth_headers, ebooks_root):
        ebook, owner_h = self._published_with_file(client, db, make_user,
                                                   auth_headers, "dl-draft@lib.com")
        client.post(f"/api/v1/library/{ebook.id}/unpublish", headers=owner_h)
        assert client.get(f"/api/v1/library/{ebook.id}/download",
                          headers=owner_h).status_code == 200
        admin = make_user(role="admin", email="dl-draft-admin@lib.com")
        admin_h = _admin_headers(client, db, admin)
        assert client.get(f"/api/v1/library/{ebook.id}/download",
                          headers=admin_h).status_code == 200

    def test_unpublish_keeps_access(self, client, db, make_user, auth_headers,
                                    ebooks_root):
        ebook, owner_h = self._published_with_file(client, db, make_user,
                                                   auth_headers, "dl-d@lib.com")
        student = make_user(role="student", email="dl-keeper@lib.com")
        _grant(db, ebook, student)
        client.post(f"/api/v1/library/{ebook.id}/unpublish", headers=owner_h)
        r = client.get(f"/api/v1/library/{ebook.id}/download",
                       headers=auth_headers(student.user_email))
        assert r.status_code == 200                        # spec section 4, BINDING
        assert r.content == PDF_BYTES

    def test_missing_file_on_disk_404_not_500(self, client, db, make_user,
                                              auth_headers, ebooks_root):
        ebook, _ = self._published_with_file(client, db, make_user, auth_headers,
                                             "dl-gone@lib.com")
        student = make_user(role="student", email="dl-gone-stu@lib.com")
        _grant(db, ebook, student)
        (ebooks_root / ebook.file_path).unlink()
        r = client.get(f"/api/v1/library/{ebook.id}/download",
                       headers=auth_headers(student.user_email))
        assert r.status_code == 404

    def test_no_file_uploaded_404(self, client, db, make_user, auth_headers,
                                  ebooks_root):
        owner = _make_approved_instructor(db, make_user, "dl-nofile@lib.com")
        ebook = _make_ebook(db, owner, status="published")
        student = make_user(role="student", email="dl-nofile-stu@lib.com")
        _grant(db, ebook, student)
        r = client.get(f"/api/v1/library/{ebook.id}/download",
                       headers=auth_headers(student.user_email))
        assert r.status_code == 404

    def test_download_unknown_id_404(self, client, db, make_user, auth_headers):
        student = make_user(role="student", email="dl-unknown@lib.com")
        r = client.get("/api/v1/library/99999/download",
                       headers=auth_headers(student.user_email))
        assert r.status_code == 404

    def test_download_non_integer_id_never_reaches_storage(self, client, db,
                                                           make_user, auth_headers):
        """The id path param is typed int - a traversal payload can never
        reach the storage layer."""
        student = make_user(role="student", email="dl-trav@lib.com")
        h = auth_headers(student.user_email)
        for probe in ["..", "..%2F..%2Fetc%2Fpasswd", "1;drop"]:
            r = client.get(f"/api/v1/library/{probe}/download", headers=h)
            assert r.status_code in (404, 422), probe

    def test_epub_download_media_type_from_stored_extension(
            self, client, db, make_user, auth_headers, ebooks_root):
        owner = _make_approved_instructor(db, make_user, "dl-epub@lib.com")
        h = auth_headers(owner.user_email)
        ebook_id = client.post("/api/v1/library", json=_create_payload(),
                               headers=h).json()["id"]
        r = client.post(f"/api/v1/library/{ebook_id}/file",
                        files={"file": ("b.epub", _epub_bytes(),
                                        "application/epub+zip")}, headers=h)
        assert r.status_code == 200, r.text
        client.post(f"/api/v1/library/{ebook_id}/publish", headers=h)
        r = client.get(f"/api/v1/library/{ebook_id}/download", headers=h)
        assert r.status_code == 200
        assert r.headers["content-type"].startswith("application/epub+zip")
        assert ".epub" in r.headers["content-disposition"]

    def test_sample_public_when_published(self, client, db, make_user,
                                          auth_headers, ebooks_root):
        ebook, owner_h = self._published_with_file(client, db, make_user,
                                                   auth_headers, "dl-e@lib.com",
                                                   sample=True)
        r = client.get(f"/api/v1/library/{ebook.id}/sample")   # NO auth header
        assert r.status_code == 200
        assert r.content == PDF_BYTES
        assert r.headers["content-type"].startswith("application/pdf")
        assert "s-maxage" not in r.headers.get("Cache-Control", "")
        client.post(f"/api/v1/library/{ebook.id}/unpublish", headers=owner_h)
        assert client.get(f"/api/v1/library/{ebook.id}/sample").status_code == 404
        # owner still reaches the sample of the draft
        assert client.get(f"/api/v1/library/{ebook.id}/sample",
                          headers=owner_h).status_code == 200

    def test_sample_draft_404_to_student_with_grant(self, client, db, make_user,
                                                    auth_headers, ebooks_root):
        ebook, owner_h = self._published_with_file(client, db, make_user,
                                                   auth_headers, "dl-g@lib.com",
                                                   sample=True)
        client.post(f"/api/v1/library/{ebook.id}/unpublish", headers=owner_h)
        student = make_user(role="student", email="dl-g-stu@lib.com")
        _grant(db, ebook, student)
        r = client.get(f"/api/v1/library/{ebook.id}/sample",
                       headers=auth_headers(student.user_email))
        assert r.status_code == 404

    def test_sample_missing_404(self, client, db, make_user, auth_headers,
                                ebooks_root):
        ebook, _ = self._published_with_file(client, db, make_user, auth_headers,
                                             "dl-f@lib.com", sample=False)
        assert client.get(f"/api/v1/library/{ebook.id}/sample").status_code == 404

    def test_sample_missing_file_on_disk_404_not_500(self, client, db, make_user,
                                                     auth_headers, ebooks_root):
        ebook, _ = self._published_with_file(client, db, make_user, auth_headers,
                                             "dl-h@lib.com", sample=True)
        (ebooks_root / ebook.sample_path).unlink()
        assert client.get(f"/api/v1/library/{ebook.id}/sample").status_code == 404


# ============================================================================
# Task 4 add-ons: controller rulings from the Task 3 review
# ============================================================================


def _completed_order(db, user, ebook, *, total, status="completed",
                     payment_method="razorpay"):
    """One Order + its ebook OrderItem line, at the given order status."""
    from app.models.payment import OrderStatus
    order = Order(
        user_id=user.id,
        order_key=f"ok-{user.id}-{ebook.id}-{status}-{total}",
        ebook_id=ebook.id,
        order_status=OrderStatus(status) if not isinstance(status, OrderStatus)
        else status,
        total_amount=total,
        payment_method=payment_method,
    )
    db.add(order)
    db.flush()
    db.add(OrderItem(order_id=order.id, course_id=None, ebook_id=ebook.id,
                     order_item_name=ebook.title, quantity=1,
                     subtotal=total, total=total))
    db.commit()
    return order


class TestSalesRevenueAccuracy:
    def test_gross_counts_completed_non_mock_orders_only(self, client, db,
                                                         make_user, auth_headers):
        owner = _make_approved_instructor(db, make_user, "rev-a@lib.com")
        buyer = make_user(role="student", email="rev-a-buyer@lib.com")
        ebook = _make_ebook(db, owner, status="published", price=500)
        _completed_order(db, buyer, ebook, total=500, status="completed")
        _completed_order(db, buyer, ebook, total=500, status="refunded")
        _completed_order(db, buyer, ebook, total=500, status="cancelled")
        _completed_order(db, buyer, ebook, total=500, status="pending")
        r = client.get(f"/api/v1/library/{ebook.id}/sales",
                       headers=auth_headers(owner.user_email))
        assert r.status_code == 200, r.text
        assert r.json()["gross_inr"] == 500.0   # not 2000 — only the COMPLETED one

    def test_mock_payment_method_excluded(self, client, db, make_user, auth_headers):
        owner = _make_approved_instructor(db, make_user, "rev-b@lib.com")
        buyer = make_user(role="student", email="rev-b-buyer@lib.com")
        ebook = _make_ebook(db, owner, status="published", price=500)
        _completed_order(db, buyer, ebook, total=500, status="completed",
                         payment_method="mock")
        r = client.get(f"/api/v1/library/{ebook.id}/sales",
                       headers=auth_headers(owner.user_email))
        assert r.json()["gross_inr"] == 0.0


class TestBlankTitleRejected:
    def test_create_whitespace_title_422(self, client, db, make_user, auth_headers):
        owner = _make_approved_instructor(db, make_user, "blank-a@lib.com")
        r = client.post("/api/v1/library", json=_create_payload(title="   "),
                        headers=auth_headers(owner.user_email))
        assert r.status_code == 422

    def test_update_whitespace_title_422_and_published_keeps_title(
            self, client, db, make_user, auth_headers):
        owner = _make_approved_instructor(db, make_user, "blank-b@lib.com")
        ebook = _make_ebook(db, owner, title="Real Title", status="published",
                            file_path="1/x.pdf")
        h = auth_headers(owner.user_email)
        r = client.put(f"/api/v1/library/{ebook.id}", json={"title": "   "},
                       headers=h)
        assert r.status_code == 422
        db.expire_all()
        assert db.query(Ebook).get(ebook.id).title == "Real Title"


class TestSlugCollision:
    def test_create_with_taken_slug_dedupes_not_500(self, client, db, make_user,
                                                    auth_headers):
        owner = _make_approved_instructor(db, make_user, "slug-a@lib.com")
        h = auth_headers(owner.user_email)
        first = client.post("/api/v1/library", json=_create_payload(), headers=h)
        assert first.status_code == 200, first.text
        taken = first.json()["slug"]
        # Park a squatter row on the slug the NEXT create would derive.
        squatter = _make_ebook(db, owner, title="Squatter")
        next_id = squatter.id + 1
        squatter.slug = f"tamil-grammar-guide-{next_id}"
        db.commit()

        second = client.post("/api/v1/library", json=_create_payload(), headers=h)
        assert second.status_code == 200, second.text
        assert second.json()["slug"] not in (taken, squatter.slug)

    def test_update_into_taken_slug_dedupes_not_500(self, client, db, make_user,
                                                    auth_headers):
        owner = _make_approved_instructor(db, make_user, "slug-b@lib.com")
        h = auth_headers(owner.user_email)
        target = _make_ebook(db, owner, title="Target Book")
        mover = _make_ebook(db, owner, title="Mover Book")
        target.slug = f"renamed-book-{mover.id}"   # exactly what mover would derive
        db.commit()
        r = client.put(f"/api/v1/library/{mover.id}",
                       json={"title": "Renamed Book"}, headers=h)
        assert r.status_code == 200, r.text
        assert r.json()["slug"] != target.slug


class TestCoverImageScheme:
    @pytest.mark.parametrize("bad", [
        "javascript:alert(1)",
        "data:text/html;base64,PHNjcmlwdD4=",
        "//evil.example.com/x.png",
        "vbscript:msgbox(1)",
        "file:///etc/passwd",
    ])
    def test_dangerous_cover_rejected(self, client, db, make_user, auth_headers, bad):
        owner = _make_approved_instructor(db, make_user, f"cov-{abs(hash(bad))%9999}@lib.com")
        r = client.post("/api/v1/library", json=_create_payload(cover_image=bad),
                        headers=auth_headers(owner.user_email))
        assert r.status_code == 422, bad

    @pytest.mark.parametrize("ok", [
        "", "https://cdn.example.com/a.png", "http://cdn.example.com/a.png",
        "/uploads/covers/a.png",
    ])
    def test_safe_cover_accepted(self, client, db, make_user, auth_headers, ok):
        owner = _make_approved_instructor(db, make_user, f"covok-{abs(hash(ok))%9999}@lib.com")
        r = client.post("/api/v1/library", json=_create_payload(cover_image=ok),
                        headers=auth_headers(owner.user_email))
        assert r.status_code == 200, r.text

    def test_update_rejects_dangerous_cover(self, client, db, make_user, auth_headers):
        owner = _make_approved_instructor(db, make_user, "cov-put@lib.com")
        ebook = _make_ebook(db, owner)
        r = client.put(f"/api/v1/library/{ebook.id}",
                       json={"cover_image": "javascript:alert(1)"},
                       headers=auth_headers(owner.user_email))
        assert r.status_code == 422


class TestDeleteMoneyTrail:
    def test_delete_409_when_order_item_references_ebook(self, client, db,
                                                         make_user, auth_headers):
        """No grant left (refunded), but the order line still points here —
        deleting would dangle the money trail."""
        owner = _make_approved_instructor(db, make_user, "del-money@lib.com")
        buyer = make_user(role="student", email="del-money-buyer@lib.com")
        ebook = _make_ebook(db, owner, status="published", price=300)
        _completed_order(db, buyer, ebook, total=300, status="refunded")
        assert db.query(EbookGrant).filter(
            EbookGrant.ebook_id == ebook.id).count() == 0
        r = client.delete(f"/api/v1/library/{ebook.id}",
                          headers=auth_headers(owner.user_email))
        assert r.status_code == 409
        assert db.query(Ebook).get(ebook.id) is not None

    def test_delete_still_works_with_no_grants_and_no_orders(self, client, db,
                                                             make_user, auth_headers):
        owner = _make_approved_instructor(db, make_user, "del-clean@lib.com")
        ebook = _make_ebook(db, owner)
        ebook_id = ebook.id
        r = client.delete(f"/api/v1/library/{ebook_id}",
                          headers=auth_headers(owner.user_email))
        assert r.status_code == 200
        db.expire_all()
        assert db.query(Ebook).filter(Ebook.id == ebook_id).first() is None


class TestPagination:
    def test_mine_pagination(self, client, db, make_user, auth_headers):
        owner = _make_approved_instructor(db, make_user, "page-a@lib.com")
        for i in range(7):
            _make_ebook(db, owner, title=f"Paged {i}")
        h = auth_headers(owner.user_email)
        r = client.get("/api/v1/library/mine", params={"limit": 3}, headers=h)
        assert r.status_code == 200
        body = r.json()
        assert len(body["ebooks"]) == 3
        assert body["count"] == 3
        assert body["total"] == 7
        r2 = client.get("/api/v1/library/mine",
                        params={"limit": 3, "offset": 6}, headers=h)
        assert len(r2.json()["ebooks"]) == 1
        # caps
        assert client.get("/api/v1/library/mine", params={"limit": 500},
                          headers=h).status_code == 422
        assert client.get("/api/v1/library/mine", params={"limit": 0},
                          headers=h).status_code == 422
        assert client.get("/api/v1/library/mine", params={"offset": -1},
                          headers=h).status_code == 422

    def test_mine_default_limit_50(self, client, db, make_user, auth_headers):
        owner = _make_approved_instructor(db, make_user, "page-b@lib.com")
        for i in range(52):
            _make_ebook(db, owner, title=f"Bulk {i}")
        r = client.get("/api/v1/library/mine",
                       headers=auth_headers(owner.user_email))
        assert len(r.json()["ebooks"]) == 50
        assert r.json()["total"] == 52

    def test_sales_buyers_paginated(self, client, db, make_user, auth_headers):
        owner = _make_approved_instructor(db, make_user, "page-c@lib.com")
        ebook = _make_ebook(db, owner, status="published")
        for i in range(5):
            _grant(db, ebook, make_user(role="student", email=f"pc{i}@lib.com"))
        h = auth_headers(owner.user_email)
        r = client.get(f"/api/v1/library/{ebook.id}/sales",
                       params={"limit": 2}, headers=h)
        assert r.status_code == 200
        body = r.json()
        assert len(body["buyers"]) == 2
        assert body["count"] == 5          # total grants, not the page size
        r2 = client.get(f"/api/v1/library/{ebook.id}/sales",
                        params={"limit": 2, "offset": 4}, headers=h)
        assert len(r2.json()["buyers"]) == 1


class TestStrictIntPrices:
    @pytest.mark.parametrize("field,value", [
        ("price_inr", True), ("price_inr", False), ("price_inr", 1.5),
        ("price_inr", "299"), ("discount_price_inr", True),
        ("discount_price_inr", 1.5),
    ])
    def test_non_int_prices_rejected(self, client, db, make_user, auth_headers,
                                     field, value):
        owner = _make_approved_instructor(
            db, make_user, f"si-{field}-{str(value)}@lib.com".replace(" ", ""))
        r = client.post("/api/v1/library", json=_create_payload(**{field: value}),
                        headers=auth_headers(owner.user_email))
        assert r.status_code == 422, (field, value)


class TestUploadRollbackAndQuota:
    def test_first_upload_rollback_leaves_no_row_change_no_orphan(
            self, client, db, make_user, auth_headers, ebooks_root, monkeypatch):
        owner = _make_approved_instructor(db, make_user, "roll-a@lib.com")
        h = auth_headers(owner.user_email)
        ebook_id = client.post("/api/v1/library", json=_create_payload(),
                               headers=h).json()["id"]
        from sqlalchemy.orm import Session as _S
        real_commit = _S.commit

        def boom(self, *a, **k):
            raise RuntimeError("db exploded")
        monkeypatch.setattr(_S, "commit", boom)
        try:
            r = client.post(f"/api/v1/library/{ebook_id}/file",
                            files={"file": ("f.pdf", PDF_BYTES, "application/pdf")},
                            headers=h)
        except RuntimeError:
            r = None
        monkeypatch.setattr(_S, "commit", real_commit)
        if r is not None:
            assert r.status_code >= 500
        db.expire_all()
        assert db.query(Ebook).get(ebook_id).file_path is None
        blobs = [p for p in ebooks_root.rglob("*") if p.is_file()] \
            if ebooks_root.exists() else []
        assert blobs == []          # the just-written blob was cleaned up

    def test_replace_upload_rollback_keeps_old_file_and_no_orphan(
            self, client, db, make_user, auth_headers, ebooks_root, monkeypatch):
        owner = _make_approved_instructor(db, make_user, "roll-b@lib.com")
        h = auth_headers(owner.user_email)
        ebook_id = client.post("/api/v1/library", json=_create_payload(),
                               headers=h).json()["id"]
        client.post(f"/api/v1/library/{ebook_id}/file",
                    files={"file": ("f.pdf", PDF_BYTES, "application/pdf")},
                    headers=h)
        db.expire_all()
        original = db.query(Ebook).get(ebook_id).file_path
        assert original and (ebooks_root / original).is_file()

        from sqlalchemy.orm import Session as _S
        real_commit = _S.commit

        def boom(self, *a, **k):
            raise RuntimeError("db exploded")
        monkeypatch.setattr(_S, "commit", boom)
        try:
            client.post(f"/api/v1/library/{ebook_id}/file",
                        files={"file": ("g.pdf", PDF_BYTES, "application/pdf")},
                        headers=h)
        except RuntimeError:
            pass
        monkeypatch.setattr(_S, "commit", real_commit)
        db.expire_all()
        assert db.query(Ebook).get(ebook_id).file_path == original
        assert (ebooks_root / original).is_file()          # old blob intact
        blobs = sorted(p.name for p in ebooks_root.rglob("*") if p.is_file())
        assert blobs == [Path(original).name]              # no orphan left behind

    def test_router_upload_over_owner_quota_413(self, client, db, make_user,
                                                auth_headers, ebooks_root,
                                                monkeypatch):
        from app.services import library_storage
        monkeypatch.setattr(library_storage, "MAX_OWNER_TOTAL_BYTES", 10)
        owner = _make_approved_instructor(db, make_user, "quota-r@lib.com")
        h = auth_headers(owner.user_email)
        ebook_id = client.post("/api/v1/library", json=_create_payload(),
                               headers=h).json()["id"]
        r = client.post(f"/api/v1/library/{ebook_id}/file",
                        files={"file": ("f.pdf", PDF_BYTES, "application/pdf")},
                        headers=h)
        assert r.status_code == 413
        db.expire_all()
        assert db.query(Ebook).get(ebook_id).file_path is None
        blobs = [p for p in ebooks_root.rglob("*") if p.is_file()] \
            if ebooks_root.exists() else []
        assert blobs == []
