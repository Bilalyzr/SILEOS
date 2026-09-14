"""H5P backend (Task 4 of the Learning Experience plan).

Covers spec docs/superpowers/specs/2026-09-02-learning-experience-design.md
section B, items 4/5/8:

  - app/services/h5p_service.py hardened zip validation/extraction:
    traversal, absolute path, oversize (declared + zip-bomb lying-header),
    disallowed extension, nested zip/h5p, missing h5p.json all rejected
    with NOTHING extracted; happy-path extraction + library parsed from
    h5p.json's mainLibrary.
  - app/routers/h5p.py: finalize (direct upload), list, get, delete
    (blocked while referenced), result upsert + enrollment guard matrix,
    results rollup.
  - Lesson round-trip of lesson_content_type / h5p_content_id through the
    course lesson create/update endpoints.
"""
import io
import shutil
import zipfile
from pathlib import Path

import pytest

from app.models.course import Course, Lesson
from app.models.enrollment import Enrollment
from app.models.h5p import H5PContent, H5PResult
from app.services.h5p_service import H5PValidationError, validate_and_extract


# ----- mock Redis for the chunked-upload flow (MockRedis semantics; mirrors
# tests/test_security_fixes.py's _MockRedisStore/chunked_env) -----------------


class _MockRedisStore:
    def __init__(self):
        self.data = {}

    async def ping(self):
        return b"PONG"

    async def get(self, key):
        return self.data.get(key)

    async def set(self, key, value, **kwargs):
        self.data[key] = value
        return True

    async def setex(self, key, ttl, value):
        self.data[key] = value
        return True

    async def delete(self, key):
        self.data.pop(key, None)
        return True

    async def ttl(self, key):
        return 3600


@pytest.fixture
def chunked_env(monkeypatch):
    """Point the chunked router at a fake Redis. Deliberately does NOT
    monkeypatch _upload_dir() — h5p.py resolves H5P_TEMP_DIR/H5P_DIR from
    the real settings.UPLOAD_DIR at import time, so the chunked-upload
    assembly step and /finalize's lookup must agree on the same real
    directory (the _clean_h5p_uploads_dir autouse fixture already clears it
    before/after every test)."""
    import app.routers.chunked_upload as cu

    store = _MockRedisStore()

    async def _fake_redis():
        return store

    monkeypatch.setattr(cu, "_redis", _fake_redis)
    return store


def _chunked_h5p_upload(client, headers, zip_bytes: bytes, filename="demo.h5p"):
    """Drive the full init -> chunk -> complete flow for one h5p upload and
    return the assembled blob's filename (the `chunked_session_id` /finalize
    expects)."""
    r_init = client.post(
        "/api/v1/upload/chunked/init",
        data={
            "filename": filename,
            "file_size": len(zip_bytes),
            "content_type": "application/zip",
            "total_chunks": 1,
            "upload_type": "h5p",
        },
        headers=headers,
    )
    assert r_init.status_code == 200, r_init.text
    upload_id = r_init.json()["upload_id"]

    r_chunk = client.post(
        "/api/v1/upload/chunked/chunk",
        data={"upload_id": upload_id, "chunk_number": "0", "total_chunks": "1"},
        files={"chunk": ("chunk_0", zip_bytes, "application/octet-stream")},
        headers=headers,
    )
    assert r_chunk.status_code == 200, r_chunk.text

    r_complete = client.post(
        "/api/v1/upload/chunked/complete",
        data={"upload_id": upload_id},
        headers=headers,
    )
    assert r_complete.status_code == 200, r_complete.text
    return r_complete.json()["filename"]


# ----- filesystem cleanup (ledger pattern: real-filesystem test cleanup) ----


@pytest.fixture(autouse=True)
def _clean_h5p_uploads_dir():
    """validate_and_extract and the /finalize endpoint write to the REAL
    filesystem under UPLOAD_DIR/h5p/{public_id}/ (validated-extraction
    target, inside the static uploads root) and _h5p_temp_dir()/{user_id}/
    (raw unvalidated blobs, a SIBLING of UPLOAD_DIR — outside every static
    mount, see chunked_upload._h5p_temp_dir's docstring) — clear both
    before AND after each test so debris never leaks across tests/runs
    (mirrors test_assessment_integrity._clean_assignment_uploads_dir)."""
    from app.routers.chunked_upload import _h5p_temp_dir
    from app.routers.uploads import UPLOAD_DIR

    h5p_dir = UPLOAD_DIR / "h5p"
    h5p_temp_dir = _h5p_temp_dir()
    shutil.rmtree(h5p_dir, ignore_errors=True)
    shutil.rmtree(h5p_temp_dir, ignore_errors=True)
    yield
    shutil.rmtree(h5p_dir, ignore_errors=True)
    shutil.rmtree(h5p_temp_dir, ignore_errors=True)


# ----- factories -------------------------------------------------------------


def _make_approved_instructor(db, make_user, email):
    """make_user(role="instructor") + an approved InstructorProfile, so
    auth_headers(email) can log in (mirrors production's approval gate)."""
    from app.models.user import InstructorProfile

    instructor = make_user(role="instructor", email=email)
    profile = db.query(InstructorProfile).filter_by(user_id=instructor.id).first()
    if profile:
        profile.is_approved = True
    else:
        db.add(InstructorProfile(user_id=instructor.id, is_approved=True))
    db.commit()
    return instructor


def _admin_headers(client, db, admin):
    """Admin logins require TOTP 2FA — enrol a secret and send the current
    code (mirrors test_assessment_integrity._admin_headers)."""
    import pyotp
    from app.core import totp

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


def _make_course(db, instructor, title="H5P Course"):
    course = Course(
        post_author=instructor.id,
        post_title=title,
        post_content="content",
        post_excerpt="excerpt",
        post_status="published",
        post_name=title.lower().replace(" ", "-"),
        course_thumbnail="",
        course_price=0,
        course_level="beginner",
        course_category="Meiporul",
        course_language="English",
        course_duration="10",
    )
    db.add(course)
    db.commit()
    db.refresh(course)
    return course


def _enroll(db, user, course, status="enrolled"):
    e = Enrollment(course_id=course.id, user_id=user.id, enrollment_status=status)
    db.add(e)
    db.commit()
    db.refresh(e)
    return e


def _make_lesson(db, course, h5p_content_id=None, content_type="h5p"):
    lesson = Lesson(
        post_author=course.post_author,
        post_parent=course.id,
        post_title="H5P Lesson",
        post_content="",
        lesson_content_type=content_type,
        h5p_content_id=h5p_content_id,
    )
    db.add(lesson)
    db.commit()
    db.refresh(lesson)
    return lesson


def _make_h5p_content(db, owner, status="ready", title="Sample Content"):
    from app.services.h5p_service import generate_public_id

    content = H5PContent(
        public_id=generate_public_id(),
        owner_id=owner.id,
        title=title,
        library="H5P.InteractiveVideo 1.22",
        size_bytes=1234,
        status=status,
    )
    db.add(content)
    db.commit()
    db.refresh(content)
    return content


def _build_zip_bytes(entries: dict) -> bytes:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        for name, content in entries.items():
            zf.writestr(name, content)
    return buf.getvalue()


VALID_H5P_ENTRIES = {
    "h5p.json": '{"mainLibrary": "H5P.InteractiveVideo 1.22", "title": "Demo"}',
    "content/content.json": "{}",
    "content/video.mp4": "x" * 50,
}


# ============================================================================
# Service-level: hardened validate_and_extract
# ============================================================================


class TestValidateAndExtract:
    def test_happy_path_extracts_and_parses_library(self, tmp_path):
        zp = tmp_path / "good.h5p"
        zp.write_bytes(_build_zip_bytes(VALID_H5P_ENTRIES))
        dest = tmp_path / "dest"

        result = validate_and_extract(zp, dest)

        assert result.library == "H5P.InteractiveVideo 1.22"
        assert (dest / "h5p.json").exists()
        assert (dest / "content" / "content.json").exists()
        assert result.file_count == 3

    def test_rejects_missing_h5p_json(self, tmp_path):
        zp = tmp_path / "bad.h5p"
        zp.write_bytes(_build_zip_bytes({"content/x.json": "{}"}))
        dest = tmp_path / "dest"

        with pytest.raises(H5PValidationError):
            validate_and_extract(zp, dest)
        assert not dest.exists()

    def test_rejects_relative_traversal(self, tmp_path):
        zp = tmp_path / "bad.h5p"
        zp.write_bytes(_build_zip_bytes({"h5p.json": "{}", "../evil.txt": "haha"}))
        dest = tmp_path / "dest"

        with pytest.raises(H5PValidationError):
            validate_and_extract(zp, dest)
        assert not dest.exists()

    def test_rejects_absolute_path(self, tmp_path):
        zp = tmp_path / "bad.h5p"
        buf = io.BytesIO()
        with zipfile.ZipFile(buf, "w") as zf:
            zf.writestr(zipfile.ZipInfo("/etc/passwd"), "haha")
            zf.writestr("h5p.json", "{}")
        zp.write_bytes(buf.getvalue())
        dest = tmp_path / "dest"

        with pytest.raises(H5PValidationError):
            validate_and_extract(zp, dest)
        assert not dest.exists()

    def test_rejects_oversize_declared_per_file(self, tmp_path):
        from app.services.h5p_service import MAX_MEMBER_UNCOMPRESSED_BYTES

        zp = tmp_path / "bad.h5p"
        buf = io.BytesIO()
        with zipfile.ZipFile(buf, "w", compression=zipfile.ZIP_DEFLATED) as zf:
            zf.writestr("h5p.json", "{}")
            zf.writestr("big.txt", "a" * (MAX_MEMBER_UNCOMPRESSED_BYTES + 1024))
        zp.write_bytes(buf.getvalue())
        dest = tmp_path / "dest"

        with pytest.raises(H5PValidationError):
            validate_and_extract(zp, dest)
        assert not dest.exists()

    def test_rejects_lying_header_zip_bomb(self, tmp_path):
        """Hand-patch the local-file-header AND central-directory uncompressed
        size fields to claim a tiny size while the actual compressed stream
        decompresses to something far larger — models a genuine zip bomb.
        Proves the streamed extraction pass (not just the declared-size
        pre-check) is load-bearing: a lying header must not win."""
        import struct

        from app.services.h5p_service import MAX_MEMBER_UNCOMPRESSED_BYTES

        real_size = MAX_MEMBER_UNCOMPRESSED_BYTES + 5 * 1024 * 1024
        payload = b"A" * real_size  # highly compressible -> tiny compressed size

        zp = tmp_path / "bomb.h5p"
        buf = io.BytesIO()
        with zipfile.ZipFile(buf, "w", compression=zipfile.ZIP_DEFLATED) as zf:
            zf.writestr("h5p.json", "{}")
            zf.writestr("bomb.txt", payload)
        data = bytearray(buf.getvalue())

        lie_size = 1024

        def patch_all(sig, size_off, fnamelen_off, fname_off):
            idx = 0
            count = 0
            while True:
                idx = data.find(sig, idx)
                if idx == -1:
                    break
                fn_len = struct.unpack_from("<H", data, idx + fnamelen_off)[0]
                fname = bytes(data[idx + fname_off: idx + fname_off + fn_len])
                if fname == b"bomb.txt":
                    struct.pack_into("<I", data, idx + size_off, lie_size)
                    count += 1
                idx += 4
            return count

        # Local File Header: sig(4) ver(2) flags(2) method(2) modtime(2)
        # moddate(2) crc32(4) compsize(4) uncompsize(4)@22 fnamelen(2)@26
        # extralen(2)@28 fname@30
        patch_all(b"PK\x03\x04", size_off=22, fnamelen_off=26, fname_off=30)
        # Central Directory Header: sig(4) vermade(2) verneed(2) flags(2)
        # method(2) modtime(2) moddate(2) crc32(4) compsize(4)
        # uncompsize(4)@24 fnamelen(2)@28 extralen(2)@30 commentlen(2)@32
        # ... fname@46
        patch_all(b"PK\x01\x02", size_off=24, fnamelen_off=28, fname_off=46)

        zp.write_bytes(bytes(data))
        dest = tmp_path / "dest"

        with pytest.raises(H5PValidationError):
            validate_and_extract(zp, dest)
        assert not dest.exists()

    def test_rejects_disallowed_extension(self, tmp_path):
        zp = tmp_path / "bad.h5p"
        zp.write_bytes(_build_zip_bytes({"h5p.json": "{}", "payload.exe": "MZ..."}))
        dest = tmp_path / "dest"

        with pytest.raises(H5PValidationError):
            validate_and_extract(zp, dest)
        assert not dest.exists()

    def test_rejects_nested_zip(self, tmp_path):
        zp = tmp_path / "bad.h5p"
        zp.write_bytes(_build_zip_bytes({"h5p.json": "{}", "sub.zip": "PK\x03\x04fake"}))
        dest = tmp_path / "dest"

        with pytest.raises(H5PValidationError):
            validate_and_extract(zp, dest)
        assert not dest.exists()

    def test_rejects_nested_h5p(self, tmp_path):
        zp = tmp_path / "bad.h5p"
        zp.write_bytes(_build_zip_bytes({"h5p.json": "{}", "sub.h5p": "PK\x03\x04fake"}))
        dest = tmp_path / "dest"

        with pytest.raises(H5PValidationError):
            validate_and_extract(zp, dest)
        assert not dest.exists()

    def test_rejects_symlink(self, tmp_path):
        import stat

        zp = tmp_path / "bad.h5p"
        buf = io.BytesIO()
        with zipfile.ZipFile(buf, "w") as zf:
            zi = zipfile.ZipInfo("link.txt")
            zi.external_attr = (stat.S_IFLNK | 0o777) << 16
            zf.writestr(zi, "/etc/passwd")
            zf.writestr("h5p.json", "{}")
        zp.write_bytes(buf.getvalue())
        dest = tmp_path / "dest"

        with pytest.raises(H5PValidationError):
            validate_and_extract(zp, dest)
        assert not dest.exists()

    def test_rejects_too_many_files(self, tmp_path):
        from app.services.h5p_service import MAX_FILE_COUNT

        zp = tmp_path / "bad.h5p"
        entries = {"h5p.json": "{}"}
        for i in range(MAX_FILE_COUNT + 5):
            entries[f"content/f{i}.txt"] = "x"
        zp.write_bytes(_build_zip_bytes(entries))
        dest = tmp_path / "dest"

        with pytest.raises(H5PValidationError):
            validate_and_extract(zp, dest)
        assert not dest.exists()

    def test_rejects_not_a_zip(self, tmp_path):
        zp = tmp_path / "bad.h5p"
        zp.write_bytes(b"this is not a zip file at all")
        dest = tmp_path / "dest"

        with pytest.raises(H5PValidationError):
            validate_and_extract(zp, dest)
        assert not dest.exists()


# ============================================================================
# Router: /api/v1/h5p
# ============================================================================


class TestFinalizeEndpoint:
    def test_finalize_direct_upload_happy_path(self, client, db, make_user, auth_headers):
        instructor = _make_approved_instructor(db, make_user, "h5p_instr1@example.com")
        headers = auth_headers(instructor.user_email, instructor._test_password)

        zip_bytes = _build_zip_bytes(VALID_H5P_ENTRIES)
        r = client.post(
            "/api/v1/h5p/finalize",
            headers=headers,
            data={"title": "My Interactive Video"},
            files={"file": ("demo.h5p", zip_bytes, "application/zip")},
        )
        assert r.status_code == 200, r.text
        body = r.json()
        assert body["status"] == "ready"
        assert body["library"] == "H5P.InteractiveVideo 1.22"
        assert body["title"] == "My Interactive Video"
        assert len(body["public_id"]) == 32

        content = db.query(H5PContent).filter_by(public_id=body["public_id"]).first()
        assert content is not None
        assert content.status == "ready"

        from app.routers.uploads import UPLOAD_DIR
        extracted_dir = UPLOAD_DIR / "h5p" / body["public_id"]
        assert (extracted_dir / "h5p.json").exists()

    def test_finalize_rejects_malicious_package_and_marks_failed(self, client, db, make_user, auth_headers):
        instructor = _make_approved_instructor(db, make_user, "h5p_instr2@example.com")
        headers = auth_headers(instructor.user_email, instructor._test_password)

        zip_bytes = _build_zip_bytes({"h5p.json": "{}", "../evil.txt": "haha"})
        r = client.post(
            "/api/v1/h5p/finalize",
            headers=headers,
            files={"file": ("evil.h5p", zip_bytes, "application/zip")},
        )
        assert r.status_code == 400, r.text

        # Nothing extracted.
        from app.routers.uploads import UPLOAD_DIR
        h5p_dir = UPLOAD_DIR / "h5p"
        if h5p_dir.exists():
            assert list(h5p_dir.iterdir()) == []

        # The content row should reflect the failure, not silently vanish.
        contents = db.query(H5PContent).all()
        assert len(contents) == 1
        assert contents[0].status == "failed"

    def test_finalize_requires_instructor_role(self, client, db, make_user, auth_headers):
        student = make_user(role="student", email="h5p_student1@example.com")
        headers = auth_headers(student.user_email, student._test_password)

        zip_bytes = _build_zip_bytes(VALID_H5P_ENTRIES)
        r = client.post(
            "/api/v1/h5p/finalize",
            headers=headers,
            files={"file": ("demo.h5p", zip_bytes, "application/zip")},
        )
        assert r.status_code == 403

    def test_finalize_rejects_bad_extension(self, client, db, make_user, auth_headers):
        instructor = _make_approved_instructor(db, make_user, "h5p_instr3@example.com")
        headers = auth_headers(instructor.user_email, instructor._test_password)

        r = client.post(
            "/api/v1/h5p/finalize",
            headers=headers,
            files={"file": ("demo.exe", b"MZ...", "application/octet-stream")},
        )
        assert r.status_code == 400


class TestListAndGet:
    def test_list_shows_own_only_for_instructor(self, client, db, make_user, auth_headers):
        i1 = _make_approved_instructor(db, make_user, "h5p_list1@example.com")
        i2 = _make_approved_instructor(db, make_user, "h5p_list2@example.com")
        _make_h5p_content(db, i1, title="Mine")
        _make_h5p_content(db, i2, title="NotMine")

        headers = auth_headers(i1.user_email, i1._test_password)
        r = client.get("/api/v1/h5p/", headers=headers)
        assert r.status_code == 200, r.text
        titles = [c["title"] for c in r.json()["contents"]]
        assert titles == ["Mine"]

    def test_list_shows_all_for_admin(self, client, db, make_user, auth_headers):
        i1 = _make_approved_instructor(db, make_user, "h5p_list3@example.com")
        i2 = _make_approved_instructor(db, make_user, "h5p_list4@example.com")
        _make_h5p_content(db, i1, title="A")
        _make_h5p_content(db, i2, title="B")

        admin = make_user(role="admin", email="h5p_admin1@example.com")
        headers = _admin_headers(client, db, admin)
        r = client.get("/api/v1/h5p/", headers=headers)
        assert r.status_code == 200, r.text
        assert len(r.json()["contents"]) == 2

    def test_list_exposes_attached_lesson_count(self, client, db, make_user, auth_headers):
        """I-H4: the instructor H5P Library page shows how many lessons still
        reference each package (DELETE 409s while > 0), so the list endpoint
        must surface that count per row."""
        instructor = _make_approved_instructor(db, make_user, "h5p_list_cnt@example.com")
        attached = _make_h5p_content(db, instructor, title="Attached")
        loose = _make_h5p_content(db, instructor, title="Loose")
        course = _make_course(db, instructor, title="Count Course")
        _make_lesson(db, course, h5p_content_id=attached.id)
        _make_lesson(db, course, h5p_content_id=attached.id)

        headers = auth_headers(instructor.user_email, instructor._test_password)
        r = client.get("/api/v1/h5p/", headers=headers)
        assert r.status_code == 200, r.text
        by_title = {c["title"]: c for c in r.json()["contents"]}
        assert by_title["Attached"]["attached_lesson_count"] == 2
        assert by_title["Loose"]["attached_lesson_count"] == 0

    def test_get_meta_owner_ok(self, client, db, make_user, auth_headers):
        instructor = _make_approved_instructor(db, make_user, "h5p_get1@example.com")
        content = _make_h5p_content(db, instructor)
        headers = auth_headers(instructor.user_email, instructor._test_password)

        r = client.get(f"/api/v1/h5p/{content.public_id}", headers=headers)
        assert r.status_code == 200, r.text
        assert r.json()["public_id"] == content.public_id

    def test_get_meta_unrelated_user_forbidden(self, client, db, make_user, auth_headers):
        instructor = _make_approved_instructor(db, make_user, "h5p_get2@example.com")
        content = _make_h5p_content(db, instructor)

        other_student = make_user(role="student", email="h5p_get_student@example.com")
        headers = auth_headers(other_student.user_email, other_student._test_password)

        r = client.get(f"/api/v1/h5p/{content.public_id}", headers=headers)
        assert r.status_code == 403

    def test_get_meta_enrolled_student_via_lesson_ok(self, client, db, make_user, auth_headers):
        instructor = _make_approved_instructor(db, make_user, "h5p_get3@example.com")
        content = _make_h5p_content(db, instructor)
        course = _make_course(db, instructor)
        _make_lesson(db, course, h5p_content_id=content.id)

        student = make_user(role="student", email="h5p_get_student2@example.com")
        _enroll(db, student, course)
        headers = auth_headers(student.user_email, student._test_password)

        r = client.get(f"/api/v1/h5p/{content.public_id}", headers=headers)
        assert r.status_code == 200, r.text

    def test_get_meta_not_found(self, client, db, make_user, auth_headers):
        instructor = _make_approved_instructor(db, make_user, "h5p_get4@example.com")
        headers = auth_headers(instructor.user_email, instructor._test_password)
        r = client.get("/api/v1/h5p/deadbeef00000000deadbeef00000000", headers=headers)
        assert r.status_code == 404


class TestDelete:
    def test_delete_owner_ok_removes_files(self, client, db, make_user, auth_headers):
        from app.routers.uploads import UPLOAD_DIR

        instructor = _make_approved_instructor(db, make_user, "h5p_del1@example.com")
        headers = auth_headers(instructor.user_email, instructor._test_password)

        zip_bytes = _build_zip_bytes(VALID_H5P_ENTRIES)
        r = client.post(
            "/api/v1/h5p/finalize", headers=headers,
            files={"file": ("demo.h5p", zip_bytes, "application/zip")},
        )
        public_id = r.json()["public_id"]
        extracted_dir = UPLOAD_DIR / "h5p" / public_id
        assert extracted_dir.exists()

        r2 = client.delete(f"/api/v1/h5p/{public_id}", headers=headers)
        assert r2.status_code == 200, r2.text
        assert not extracted_dir.exists()
        assert db.query(H5PContent).filter_by(public_id=public_id).first() is None

    def test_delete_blocked_while_referenced(self, client, db, make_user, auth_headers):
        instructor = _make_approved_instructor(db, make_user, "h5p_del2@example.com")
        content = _make_h5p_content(db, instructor)
        course = _make_course(db, instructor)
        _make_lesson(db, course, h5p_content_id=content.id)

        headers = auth_headers(instructor.user_email, instructor._test_password)
        r = client.delete(f"/api/v1/h5p/{content.public_id}", headers=headers)
        assert r.status_code == 409

        assert db.query(H5PContent).filter_by(public_id=content.public_id).first() is not None

    def test_delete_forbidden_for_non_owner_instructor(self, client, db, make_user, auth_headers):
        owner = _make_approved_instructor(db, make_user, "h5p_del3@example.com")
        other = _make_approved_instructor(db, make_user, "h5p_del4@example.com")
        content = _make_h5p_content(db, owner)

        headers = auth_headers(other.user_email, other._test_password)
        r = client.delete(f"/api/v1/h5p/{content.public_id}", headers=headers)
        assert r.status_code == 403

    def test_delete_admin_ok(self, client, db, make_user, auth_headers):
        owner = _make_approved_instructor(db, make_user, "h5p_del5@example.com")
        content = _make_h5p_content(db, owner)
        admin = make_user(role="admin", email="h5p_admin2@example.com")
        headers = _admin_headers(client, db, admin)

        r = client.delete(f"/api/v1/h5p/{content.public_id}", headers=headers)
        assert r.status_code == 200, r.text


class TestResultUpsertAndEnrollmentGuard:
    def test_enrolled_student_can_submit_result(self, client, db, make_user, auth_headers):
        instructor = _make_approved_instructor(db, make_user, "h5p_res1@example.com")
        content = _make_h5p_content(db, instructor)
        course = _make_course(db, instructor)
        _make_lesson(db, course, h5p_content_id=content.id)

        student = make_user(role="student", email="h5p_res_student1@example.com")
        _enroll(db, student, course)
        headers = auth_headers(student.user_email, student._test_password)

        r = client.post(
            f"/api/v1/h5p/{content.public_id}/result",
            headers=headers,
            json={"score": 8, "max_score": 10, "completed": True},
        )
        assert r.status_code == 200, r.text
        body = r.json()
        assert body["score"] == 8
        assert body["max_score"] == 10
        assert body["completed"] is True

        row = db.query(H5PResult).filter_by(content_id=content.id, user_id=student.id).first()
        assert row is not None

    def test_result_is_upserted_not_duplicated(self, client, db, make_user, auth_headers):
        instructor = _make_approved_instructor(db, make_user, "h5p_res2@example.com")
        content = _make_h5p_content(db, instructor)
        course = _make_course(db, instructor)
        _make_lesson(db, course, h5p_content_id=content.id)

        student = make_user(role="student", email="h5p_res_student2@example.com")
        _enroll(db, student, course)
        headers = auth_headers(student.user_email, student._test_password)

        client.post(
            f"/api/v1/h5p/{content.public_id}/result", headers=headers,
            json={"score": 5, "max_score": 10, "completed": False},
        )
        r2 = client.post(
            f"/api/v1/h5p/{content.public_id}/result", headers=headers,
            json={"score": 9, "max_score": 10, "completed": True},
        )
        assert r2.status_code == 200, r2.text

        rows = db.query(H5PResult).filter_by(content_id=content.id, user_id=student.id).all()
        assert len(rows) == 1
        assert rows[0].score == 9
        assert rows[0].completed is True

    def test_unenrolled_user_rejected(self, client, db, make_user, auth_headers):
        instructor = _make_approved_instructor(db, make_user, "h5p_res3@example.com")
        content = _make_h5p_content(db, instructor)
        course = _make_course(db, instructor)
        _make_lesson(db, course, h5p_content_id=content.id)

        outsider = make_user(role="student", email="h5p_res_outsider@example.com")
        headers = auth_headers(outsider.user_email, outsider._test_password)

        r = client.post(
            f"/api/v1/h5p/{content.public_id}/result", headers=headers,
            json={"score": 5, "max_score": 10, "completed": False},
        )
        assert r.status_code == 403

    def test_no_referencing_lesson_rejected_even_if_enrolled_elsewhere(self, client, db, make_user, auth_headers):
        instructor = _make_approved_instructor(db, make_user, "h5p_res4@example.com")
        content = _make_h5p_content(db, instructor)
        # Content exists but no lesson references it at all.
        course = _make_course(db, instructor)

        student = make_user(role="student", email="h5p_res_student4@example.com")
        _enroll(db, student, course)
        headers = auth_headers(student.user_email, student._test_password)

        r = client.post(
            f"/api/v1/h5p/{content.public_id}/result", headers=headers,
            json={"score": 5, "max_score": 10, "completed": False},
        )
        assert r.status_code == 403

    def test_cancelled_enrollment_rejected(self, client, db, make_user, auth_headers):
        instructor = _make_approved_instructor(db, make_user, "h5p_res5@example.com")
        content = _make_h5p_content(db, instructor)
        course = _make_course(db, instructor)
        _make_lesson(db, course, h5p_content_id=content.id)

        student = make_user(role="student", email="h5p_res_student5@example.com")
        _enroll(db, student, course, status="cancelled")
        headers = auth_headers(student.user_email, student._test_password)

        r = client.post(
            f"/api/v1/h5p/{content.public_id}/result", headers=headers,
            json={"score": 5, "max_score": 10, "completed": False},
        )
        assert r.status_code == 403

    def test_owner_instructor_can_submit_result_without_enrollment(self, client, db, make_user, auth_headers):
        """Owner previewing their own content shouldn't need a student
        enrollment row — admin/owner bypass mirrors other routers' testing
        convenience guards."""
        instructor = _make_approved_instructor(db, make_user, "h5p_res6@example.com")
        content = _make_h5p_content(db, instructor)
        course = _make_course(db, instructor)
        _make_lesson(db, course, h5p_content_id=content.id)
        headers = auth_headers(instructor.user_email, instructor._test_password)

        r = client.post(
            f"/api/v1/h5p/{content.public_id}/result", headers=headers,
            json={"score": 5, "max_score": 10, "completed": False},
        )
        assert r.status_code == 200, r.text

    def test_score_bounds_validated(self, client, db, make_user, auth_headers):
        instructor = _make_approved_instructor(db, make_user, "h5p_res7@example.com")
        content = _make_h5p_content(db, instructor)
        course = _make_course(db, instructor)
        _make_lesson(db, course, h5p_content_id=content.id)

        student = make_user(role="student", email="h5p_res_student7@example.com")
        _enroll(db, student, course)
        headers = auth_headers(student.user_email, student._test_password)

        # score > max_score
        r = client.post(
            f"/api/v1/h5p/{content.public_id}/result", headers=headers,
            json={"score": 20, "max_score": 10, "completed": True},
        )
        assert r.status_code == 400

        # negative score
        r2 = client.post(
            f"/api/v1/h5p/{content.public_id}/result", headers=headers,
            json={"score": -1, "max_score": 10, "completed": True},
        )
        assert r2.status_code == 400

        # max_score above ceiling
        r3 = client.post(
            f"/api/v1/h5p/{content.public_id}/result", headers=headers,
            json={"score": 5, "max_score": 999999, "completed": True},
        )
        assert r3.status_code == 400

    def test_result_without_score_completed_only(self, client, db, make_user, auth_headers):
        instructor = _make_approved_instructor(db, make_user, "h5p_res8@example.com")
        content = _make_h5p_content(db, instructor)
        course = _make_course(db, instructor)
        _make_lesson(db, course, h5p_content_id=content.id)

        student = make_user(role="student", email="h5p_res_student8@example.com")
        _enroll(db, student, course)
        headers = auth_headers(student.user_email, student._test_password)

        r = client.post(
            f"/api/v1/h5p/{content.public_id}/result", headers=headers,
            json={"completed": True},
        )
        assert r.status_code == 200, r.text
        assert r.json()["completed"] is True
        assert r.json()["score"] is None


class TestResultsRollup:
    def test_owner_can_view_rollup(self, client, db, make_user, auth_headers):
        instructor = _make_approved_instructor(db, make_user, "h5p_roll1@example.com")
        content = _make_h5p_content(db, instructor)
        course = _make_course(db, instructor)
        _make_lesson(db, course, h5p_content_id=content.id)

        s1 = make_user(role="student", email="h5p_roll_s1@example.com")
        s2 = make_user(role="student", email="h5p_roll_s2@example.com")
        _enroll(db, s1, course)
        _enroll(db, s2, course)
        h1 = auth_headers(s1.user_email, s1._test_password)
        h2 = auth_headers(s2.user_email, s2._test_password)
        client.post(f"/api/v1/h5p/{content.public_id}/result", headers=h1, json={"score": 7, "max_score": 10, "completed": True})
        client.post(f"/api/v1/h5p/{content.public_id}/result", headers=h2, json={"score": 3, "max_score": 10, "completed": False})

        owner_headers = auth_headers(instructor.user_email, instructor._test_password)
        r = client.get(f"/api/v1/h5p/{content.public_id}/results", headers=owner_headers)
        assert r.status_code == 200, r.text
        assert r.json()["count"] == 2

    def test_non_owner_instructor_forbidden_from_rollup(self, client, db, make_user, auth_headers):
        owner = _make_approved_instructor(db, make_user, "h5p_roll2@example.com")
        other = _make_approved_instructor(db, make_user, "h5p_roll3@example.com")
        content = _make_h5p_content(db, owner)

        headers = auth_headers(other.user_email, other._test_password)
        r = client.get(f"/api/v1/h5p/{content.public_id}/results", headers=headers)
        assert r.status_code == 403


# ============================================================================
# Lesson round-trip of the two new fields
# ============================================================================


class TestLessonFieldRoundTrip:
    def test_create_lesson_with_h5p_content_type(self, client, db, make_user, auth_headers):
        instructor = _make_approved_instructor(db, make_user, "h5p_lesson1@example.com")
        content = _make_h5p_content(db, instructor)
        course = _make_course(db, instructor)
        headers = auth_headers(instructor.user_email, instructor._test_password)

        r = client.post(
            f"/api/v1/courses/{course.id}/lessons",
            headers=headers,
            json={
                "title": "Interactive Lesson",
                "content": "",
                "lesson_content_type": "h5p",
                "h5p_content_id": content.id,
            },
        )
        assert r.status_code == 200, r.text
        body = r.json()
        assert body["lesson_content_type"] == "h5p"
        assert body["h5p_content_id"] == content.id

        lesson = db.query(Lesson).filter_by(id=body["id"]).first()
        assert lesson.lesson_content_type == "h5p"
        assert lesson.h5p_content_id == content.id

    def test_create_lesson_defaults_to_video(self, client, db, make_user, auth_headers):
        instructor = _make_approved_instructor(db, make_user, "h5p_lesson2@example.com")
        course = _make_course(db, instructor)
        headers = auth_headers(instructor.user_email, instructor._test_password)

        r = client.post(
            f"/api/v1/courses/{course.id}/lessons",
            headers=headers,
            json={"title": "Video Lesson", "content": ""},
        )
        assert r.status_code == 200, r.text
        assert r.json()["lesson_content_type"] == "video"
        assert r.json()["h5p_content_id"] is None

    def test_update_lesson_switches_to_h5p(self, client, db, make_user, auth_headers):
        instructor = _make_approved_instructor(db, make_user, "h5p_lesson3@example.com")
        content = _make_h5p_content(db, instructor)
        course = _make_course(db, instructor)
        lesson = _make_lesson(db, course, h5p_content_id=None, content_type="video")
        headers = auth_headers(instructor.user_email, instructor._test_password)

        r = client.patch(
            f"/api/v1/courses/{course.id}/lessons/{lesson.id}",
            headers=headers,
            json={"lesson_content_type": "h5p", "h5p_content_id": content.id},
        )
        assert r.status_code == 200, r.text
        assert r.json()["lesson_content_type"] == "h5p"
        assert r.json()["h5p_content_id"] == content.id

    def test_get_course_includes_lesson_h5p_fields(self, client, db, make_user, auth_headers):
        instructor = _make_approved_instructor(db, make_user, "h5p_lesson4@example.com")
        content = _make_h5p_content(db, instructor)
        course = _make_course(db, instructor)
        _make_lesson(db, course, h5p_content_id=content.id)
        headers = auth_headers(instructor.user_email, instructor._test_password)

        r = client.get(f"/api/v1/courses/{course.id}", headers=headers)
        assert r.status_code == 200, r.text
        lessons = r.json()["lessons"]
        assert len(lessons) == 1
        assert lessons[0]["lesson_content_type"] == "h5p"
        assert lessons[0]["h5p_content_id"] == content.id

    def test_get_course_resolves_h5p_public_id_for_the_frontend_player(self, client, db, make_user, auth_headers):
        """The H5P frontend player (H5PLesson.tsx / h5p-player.html) routes
        by public_id, never the integer h5p_content_id FK — GET /courses/{id}
        must resolve and embed it so the lesson response is directly usable
        without a second round-trip the student has no endpoint for (only
        instructors/admins/enrolled-course viewers can GET /h5p/{public_id},
        and that still requires already knowing the public_id)."""
        instructor = _make_approved_instructor(db, make_user, "h5p_lesson5@example.com")
        content = _make_h5p_content(db, instructor)
        course = _make_course(db, instructor)
        _make_lesson(db, course, h5p_content_id=content.id)
        headers = auth_headers(instructor.user_email, instructor._test_password)

        r = client.get(f"/api/v1/courses/{course.id}", headers=headers)
        assert r.status_code == 200, r.text
        lessons = r.json()["lessons"]
        assert len(lessons) == 1
        assert lessons[0]["h5p_public_id"] == content.public_id

    def test_get_course_h5p_public_id_is_none_for_video_lessons(self, client, db, make_user, auth_headers):
        instructor = _make_approved_instructor(db, make_user, "h5p_lesson6@example.com")
        course = _make_course(db, instructor)
        _make_lesson(db, course, h5p_content_id=None, content_type="video")
        headers = auth_headers(instructor.user_email, instructor._test_password)

        r = client.get(f"/api/v1/courses/{course.id}", headers=headers)
        assert r.status_code == 200, r.text
        lessons = r.json()["lessons"]
        assert len(lessons) == 1
        assert lessons[0]["h5p_public_id"] is None

    def test_list_h5p_contents_exposes_integer_id_for_lesson_editor(self, client, db, make_user, auth_headers):
        """The instructor lesson editor (H5PPicker.tsx) stores h5p_content_id
        (the integer PK) on the lesson — GET /api/v1/h5p/ must expose it,
        not just public_id, or the picker has no way to select a content
        item at all."""
        instructor = _make_approved_instructor(db, make_user, "h5p_lesson7@example.com")
        content = _make_h5p_content(db, instructor)
        headers = auth_headers(instructor.user_email, instructor._test_password)

        r = client.get("/api/v1/h5p/", headers=headers)
        assert r.status_code == 200, r.text
        rows = r.json()["contents"]
        assert len(rows) == 1
        assert rows[0]["id"] == content.id
        assert rows[0]["public_id"] == content.public_id


# ============================================================================
# Review fixes (H-1, H-2, M-1, M-2, L-1..L-4): regression tests (L-5)
# ============================================================================


class TestFinalizeOwnershipIsolation:
    """H-1: chunked_session_id lookups must be scoped to the caller's own
    namespace — cross-user finalize (which also deletes the blob) must be
    impossible, and the existence-oracle must be closed (400 for anything
    outside the caller's namespace, never a 404 that leaks whether some
    *other* filename exists elsewhere)."""

    def test_cross_user_finalize_is_rejected_and_blob_untouched(self, client, db, make_user, auth_headers, chunked_env):
        from app.routers.chunked_upload import _h5p_temp_dir
        from app.routers.uploads import UPLOAD_DIR

        instr_a = _make_approved_instructor(db, make_user, "h5p_cross_a@example.com")
        instr_b = _make_approved_instructor(db, make_user, "h5p_cross_b@example.com")
        headers_a = auth_headers(instr_a.user_email, instr_a._test_password)
        headers_b = auth_headers(instr_b.user_email, instr_b._test_password)

        zip_bytes = _build_zip_bytes(VALID_H5P_ENTRIES)
        blob_filename = _chunked_h5p_upload(client, headers_a, zip_bytes)

        a_blob_path = _h5p_temp_dir() / str(instr_a.id) / blob_filename
        assert a_blob_path.exists(), "assembled blob should land in the uploader's own namespace"
        # The hazard this whole fix round closes: the assembly dir must NOT
        # be inside the statically-served uploads root.
        assert UPLOAD_DIR.resolve() not in a_blob_path.resolve().parents, (
            "h5p_temp blob must live outside the static /uploads mount"
        )

        # Instructor B tries to finalize using A's blob filename as the
        # session id — must be rejected, and A's blob must survive
        # untouched (not deleted, not consumed).
        r = client.post(
            "/api/v1/h5p/finalize",
            headers=headers_b,
            data={"chunked_session_id": blob_filename},
        )
        assert r.status_code in (400, 404), r.text
        assert a_blob_path.exists(), "instructor B's failed finalize must not delete instructor A's blob"

        # No H5PContent row should have been created for B's failed attempt.
        assert db.query(H5PContent).filter_by(owner_id=instr_b.id).count() == 0

        # A can still finalize their own blob successfully afterwards.
        r_a = client.post(
            "/api/v1/h5p/finalize",
            headers=headers_a,
            data={"chunked_session_id": blob_filename},
        )
        assert r_a.status_code == 200, r_a.text

    def test_existence_oracle_closed_for_traversal_attempt(self, client, db, make_user, auth_headers, chunked_env):
        instructor = _make_approved_instructor(db, make_user, "h5p_oracle1@example.com")
        headers = auth_headers(instructor.user_email, instructor._test_password)

        # A crafted session id trying to escape the per-user namespace via
        # traversal must be rejected as invalid (400) BEFORE any
        # exists()/is_file() check runs — never surfaced as a 404 (which
        # would mean "the path was well-formed but nothing was there",
        # i.e. an oracle for probing paths outside the sandbox).
        r = client.post(
            "/api/v1/h5p/finalize",
            headers=headers,
            data={"chunked_session_id": "../../etc/passwd"},
        )
        assert r.status_code == 400, r.text

    def test_own_namespace_missing_file_is_404(self, client, db, make_user, auth_headers, chunked_env):
        instructor = _make_approved_instructor(db, make_user, "h5p_oracle2@example.com")
        headers = auth_headers(instructor.user_email, instructor._test_password)

        # A well-formed filename that simply doesn't exist in the caller's
        # OWN namespace is still a normal 404 (containment passed; the file
        # just isn't there).
        r = client.post(
            "/api/v1/h5p/finalize",
            headers=headers,
            data={"chunked_session_id": "does-not-exist.h5p"},
        )
        assert r.status_code == 404, r.text

    def test_chunked_upload_happy_path_end_to_end(self, client, db, make_user, auth_headers, chunked_env):
        instructor = _make_approved_instructor(db, make_user, "h5p_chunked_happy@example.com")
        headers = auth_headers(instructor.user_email, instructor._test_password)

        zip_bytes = _build_zip_bytes(VALID_H5P_ENTRIES)
        blob_filename = _chunked_h5p_upload(client, headers, zip_bytes)

        r = client.post(
            "/api/v1/h5p/finalize",
            headers=headers,
            data={"chunked_session_id": blob_filename, "title": "Chunked Demo"},
        )
        assert r.status_code == 200, r.text
        assert r.json()["status"] == "ready"
        assert r.json()["library"] == "H5P.InteractiveVideo 1.22"


class TestLessonH5PFieldValidation:
    """H-2: lesson_content_type/h5p_content_id cross-field validation matrix."""

    def test_h5p_type_without_content_id_rejected(self, client, db, make_user, auth_headers):
        instructor = _make_approved_instructor(db, make_user, "h5p_lv1@example.com")
        course = _make_course(db, instructor)
        headers = auth_headers(instructor.user_email, instructor._test_password)

        r = client.post(
            f"/api/v1/courses/{course.id}/lessons",
            headers=headers,
            json={"title": "Bad Lesson", "content": "", "lesson_content_type": "h5p"},
        )
        assert r.status_code == 400, r.text

    def test_nonexistent_content_id_404(self, client, db, make_user, auth_headers):
        instructor = _make_approved_instructor(db, make_user, "h5p_lv2@example.com")
        course = _make_course(db, instructor)
        headers = auth_headers(instructor.user_email, instructor._test_password)

        r = client.post(
            f"/api/v1/courses/{course.id}/lessons",
            headers=headers,
            json={
                "title": "Bad Lesson",
                "content": "",
                "lesson_content_type": "h5p",
                "h5p_content_id": 999999,
            },
        )
        assert r.status_code == 404, r.text

    def test_failed_status_content_rejected(self, client, db, make_user, auth_headers):
        instructor = _make_approved_instructor(db, make_user, "h5p_lv3@example.com")
        content = _make_h5p_content(db, instructor, status="failed")
        course = _make_course(db, instructor)
        headers = auth_headers(instructor.user_email, instructor._test_password)

        r = client.post(
            f"/api/v1/courses/{course.id}/lessons",
            headers=headers,
            json={
                "title": "Bad Lesson",
                "content": "",
                "lesson_content_type": "h5p",
                "h5p_content_id": content.id,
            },
        )
        assert r.status_code == 400, r.text

    def test_uploaded_status_content_rejected(self, client, db, make_user, auth_headers):
        instructor = _make_approved_instructor(db, make_user, "h5p_lv3b@example.com")
        content = _make_h5p_content(db, instructor, status="uploaded")
        course = _make_course(db, instructor)
        headers = auth_headers(instructor.user_email, instructor._test_password)

        r = client.post(
            f"/api/v1/courses/{course.id}/lessons",
            headers=headers,
            json={
                "title": "Bad Lesson",
                "content": "",
                "lesson_content_type": "h5p",
                "h5p_content_id": content.id,
            },
        )
        assert r.status_code == 400, r.text

    def test_foreign_owner_content_blocked_for_instructor(self, client, db, make_user, auth_headers):
        """POLICY ADJUDICATED: cross-owner references are BLOCKED — an
        instructor may only attach their OWN H5P content to a lesson."""
        owner = _make_approved_instructor(db, make_user, "h5p_lv4_owner@example.com")
        other = _make_approved_instructor(db, make_user, "h5p_lv4_other@example.com")
        content = _make_h5p_content(db, owner, status="ready")
        course = _make_course(db, other)
        headers = auth_headers(other.user_email, other._test_password)

        r = client.post(
            f"/api/v1/courses/{course.id}/lessons",
            headers=headers,
            json={
                "title": "Bad Lesson",
                "content": "",
                "lesson_content_type": "h5p",
                "h5p_content_id": content.id,
            },
        )
        assert r.status_code == 403, r.text

    def test_admin_may_attach_any_owners_content(self, client, db, make_user, auth_headers):
        owner = _make_approved_instructor(db, make_user, "h5p_lv5_owner@example.com")
        content = _make_h5p_content(db, owner, status="ready")
        course = _make_course(db, owner)

        admin = make_user(role="admin", email="h5p_lv5_admin@example.com")
        headers = _admin_headers(client, db, admin)

        r = client.post(
            f"/api/v1/courses/{course.id}/lessons",
            headers=headers,
            json={
                "title": "Admin Lesson",
                "content": "",
                "lesson_content_type": "h5p",
                "h5p_content_id": content.id,
            },
        )
        assert r.status_code == 200, r.text
        assert r.json()["h5p_content_id"] == content.id

    def test_bogus_content_type_string_rejected(self, client, db, make_user, auth_headers):
        instructor = _make_approved_instructor(db, make_user, "h5p_lv6@example.com")
        course = _make_course(db, instructor)
        headers = auth_headers(instructor.user_email, instructor._test_password)

        r = client.post(
            f"/api/v1/courses/{course.id}/lessons",
            headers=headers,
            json={"title": "Bad Lesson", "content": "", "lesson_content_type": "pdf"},
        )
        assert r.status_code in (400, 422), r.text

    def test_switching_back_to_video_clears_content_id(self, client, db, make_user, auth_headers):
        instructor = _make_approved_instructor(db, make_user, "h5p_lv7@example.com")
        content = _make_h5p_content(db, instructor, status="ready")
        course = _make_course(db, instructor)
        lesson = _make_lesson(db, course, h5p_content_id=content.id, content_type="h5p")
        headers = auth_headers(instructor.user_email, instructor._test_password)

        r = client.patch(
            f"/api/v1/courses/{course.id}/lessons/{lesson.id}",
            headers=headers,
            json={"lesson_content_type": "video"},
        )
        assert r.status_code == 200, r.text
        assert r.json()["lesson_content_type"] == "video"
        assert r.json()["h5p_content_id"] is None

        db.refresh(lesson)
        assert lesson.h5p_content_id is None

    def test_update_with_only_h5p_content_id_keeps_existing_type_check(self, client, db, make_user, auth_headers):
        """Supplying h5p_content_id without lesson_content_type on an
        already-video lesson must still be validated (the effective type
        stays "video" here, so h5p_content_id is simply ignored/rejected
        depending on interpretation) — pin down the actual contract: since
        the lesson's existing type is "video", the effective type used by
        the resolver is "video", so h5p_content_id is dropped rather than
        erroring."""
        instructor = _make_approved_instructor(db, make_user, "h5p_lv8@example.com")
        content = _make_h5p_content(db, instructor, status="ready")
        course = _make_course(db, instructor)
        lesson = _make_lesson(db, course, h5p_content_id=None, content_type="video")
        headers = auth_headers(instructor.user_email, instructor._test_password)

        r = client.patch(
            f"/api/v1/courses/{course.id}/lessons/{lesson.id}",
            headers=headers,
            json={"h5p_content_id": content.id},
        )
        assert r.status_code == 200, r.text
        assert r.json()["lesson_content_type"] == "video"
        assert r.json()["h5p_content_id"] is None


class TestMainLibraryTruncation:
    def test_mainlibrary_over_120_chars_is_truncated(self, tmp_path):
        long_library = "H5P.SomeExtremelyLongLibraryNameThatGoesOnAndOnAndOnAndOnAndOnAndOnAndOnAndOnAndOnAndOnAndOnAndOnAndOnAndOnAndOnAndOnAndOn 1.0"
        assert len(long_library) > 120

        entries = dict(VALID_H5P_ENTRIES)
        entries["h5p.json"] = f'{{"mainLibrary": "{long_library}", "title": "t"}}'
        zp = tmp_path / "long.h5p"
        zp.write_bytes(_build_zip_bytes(entries))
        dest = tmp_path / "dest"

        result = validate_and_extract(zp, dest)
        assert len(result.library) == 120
        assert result.library == long_library[:120]


class TestOwnerAggregateCap:
    def test_upload_rejected_when_owner_would_exceed_aggregate_cap(self, client, db, make_user, auth_headers):
        instructor = _make_approved_instructor(db, make_user, "h5p_agg1@example.com")
        # Simulate the owner already sitting near the 2GB ceiling via an
        # existing `ready` row's recorded size_bytes (no need to actually
        # write 2GB to disk for this — the cap check only reads size_bytes
        # from the DB plus the new upload's DECLARED size).
        existing = _make_h5p_content(db, instructor, status="ready")
        existing.size_bytes = (2 * 1024 * 1024 * 1024) - 100  # just under 2GB
        db.commit()

        headers = auth_headers(instructor.user_email, instructor._test_password)
        # A tiny but declared-nonzero package should still push the owner
        # over the 2GB ceiling combined with the existing 2GB-100B usage.
        entries = dict(VALID_H5P_ENTRIES)
        entries["content/pad.txt"] = "x" * 1000
        zip_bytes = _build_zip_bytes(entries)

        r = client.post(
            "/api/v1/h5p/finalize",
            headers=headers,
            files={"file": ("demo.h5p", zip_bytes, "application/zip")},
        )
        assert r.status_code == 400, r.text
        assert "aggregate" in r.json()["detail"].lower() or "limit" in r.json()["detail"].lower()

    def test_upload_allowed_when_under_aggregate_cap(self, client, db, make_user, auth_headers):
        instructor = _make_approved_instructor(db, make_user, "h5p_agg2@example.com")
        headers = auth_headers(instructor.user_email, instructor._test_password)

        zip_bytes = _build_zip_bytes(VALID_H5P_ENTRIES)
        r = client.post(
            "/api/v1/h5p/finalize",
            headers=headers,
            files={"file": ("demo.h5p", zip_bytes, "application/zip")},
        )
        assert r.status_code == 200, r.text

    def test_failed_content_does_not_count_toward_cap(self, client, db, make_user, auth_headers):
        instructor = _make_approved_instructor(db, make_user, "h5p_agg3@example.com")
        failed = _make_h5p_content(db, instructor, status="failed")
        failed.size_bytes = 2 * 1024 * 1024 * 1024  # 2GB, but status=failed
        db.commit()

        headers = auth_headers(instructor.user_email, instructor._test_password)
        zip_bytes = _build_zip_bytes(VALID_H5P_ENTRIES)
        r = client.post(
            "/api/v1/h5p/finalize",
            headers=headers,
            files={"file": ("demo.h5p", zip_bytes, "application/zip")},
        )
        assert r.status_code == 200, r.text


class TestDuplicateEntriesAndMetadataSkip:
    def test_duplicate_entry_names_rejected(self, tmp_path):
        buf = io.BytesIO()
        with zipfile.ZipFile(buf, "w") as zf:
            zf.writestr("h5p.json", '{"mainLibrary": "H5P.Test 1.0"}')
            zf.writestr("content/a.txt", "first")
            zf.writestr("content/a.txt", "second")  # duplicate name
        zp = tmp_path / "dup.h5p"
        zp.write_bytes(buf.getvalue())
        dest = tmp_path / "dest"

        with pytest.raises(H5PValidationError):
            validate_and_extract(zp, dest)
        assert not dest.exists()

    def test_license_file_skipped_not_rejected(self, tmp_path):
        """A LICENSE file (no extension) must not cause the whole package
        to be rejected — it's simply absent from the extracted output."""
        entries = dict(VALID_H5P_ENTRIES)
        entries["LICENSE"] = "MIT License text goes here..."
        zp = tmp_path / "licensed.h5p"
        zp.write_bytes(_build_zip_bytes(entries))
        dest = tmp_path / "dest"

        result = validate_and_extract(zp, dest)
        assert (dest / "h5p.json").exists()
        assert not (dest / "LICENSE").exists(), "extensionless metadata files must be skipped, not extracted"

    def test_htaccess_style_dotfile_skipped(self, tmp_path):
        entries = dict(VALID_H5P_ENTRIES)
        entries[".htaccess"] = "deny from all"
        zp = tmp_path / "dotfile.h5p"
        zp.write_bytes(_build_zip_bytes(entries))
        dest = tmp_path / "dest"

        result = validate_and_extract(zp, dest)
        assert (dest / "h5p.json").exists()
        assert not (dest / ".htaccess").exists()

    def test_uppercase_html_extension_still_accepted(self, tmp_path):
        """Case-insensitive extension matching: a `.HTML` member is the same
        allowed type as `.html`, not a way to sneak past the allowlist nor
        a reason to reject an otherwise-legitimate package."""
        entries = dict(VALID_H5P_ENTRIES)
        entries["content/INDEX.HTML"] = "<html></html>"
        zp = tmp_path / "upper.h5p"
        zp.write_bytes(_build_zip_bytes(entries))
        dest = tmp_path / "dest"

        result = validate_and_extract(zp, dest)
        assert (dest / "content" / "INDEX.HTML").exists()

    def test_unknown_extension_content_like_file_still_rejected(self, tmp_path):
        """An unknown extension on a file that otherwise looks like content
        (has an extension, just not an allowlisted one) is still rejected
        outright — only extensionless names get the metadata-skip
        treatment (L-3)."""
        entries = dict(VALID_H5P_ENTRIES)
        entries["content/script.php"] = "<?php system($_GET['c']); ?>"
        zp = tmp_path / "phpfile.h5p"
        zp.write_bytes(_build_zip_bytes(entries))
        dest = tmp_path / "dest"

        with pytest.raises(H5PValidationError):
            validate_and_extract(zp, dest)
        assert not dest.exists()


class TestResultsRollupPrefetch:
    def test_rollup_returns_correct_users_with_prefetch(self, client, db, make_user, auth_headers):
        """L-4 regression: the rollup must still map each result to the
        correct user after switching from N+1 lookups to a single
        prefetched in_() query."""
        instructor = _make_approved_instructor(db, make_user, "h5p_prefetch1@example.com")
        content = _make_h5p_content(db, instructor)
        course = _make_course(db, instructor)
        _make_lesson(db, course, h5p_content_id=content.id)

        students = [
            make_user(role="student", email=f"h5p_prefetch_s{i}@example.com")
            for i in range(3)
        ]
        for s in students:
            _enroll(db, s, course)

        for i, s in enumerate(students):
            h = auth_headers(s.user_email, s._test_password)
            client.post(
                f"/api/v1/h5p/{content.public_id}/result",
                headers=h,
                json={"score": i, "max_score": 10, "completed": bool(i)},
            )

        owner_headers = auth_headers(instructor.user_email, instructor._test_password)
        r = client.get(f"/api/v1/h5p/{content.public_id}/results", headers=owner_headers)
        assert r.status_code == 200, r.text
        rows = r.json()["results"]
        assert len(rows) == 3

        rows_by_user_id = {row["user_id"]: row for row in rows}
        for i, s in enumerate(students):
            row = rows_by_user_id[s.id]
            assert row["user_name"] == s.display_name
            assert row["user_email"] == s.user_email
            assert row["score"] == i
