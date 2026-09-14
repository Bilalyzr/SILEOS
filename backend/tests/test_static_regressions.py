"""
Regression guards for defects surfaced by the 2026-09-05 static sweep
(pyflakes undefined-name findings that were live or latent runtime bugs).

Each test pins the ROOT CAUSE, not the symptom:
1. `internships.py` uses `from __future__ import annotations`, so an
   unimported `Any` in a signature does not raise at import time — FastAPI
   silently registered `payload: dict[str, Any]` as a required QUERY
   parameter and every JSON-body call 422'd with "payload: Field required".
2. `AuthService.require_role` referenced the bare name
   `get_current_active_user` (a static method) → NameError on first call.
3. `secure_upload.clean_old_files` used `timedelta` without importing it;
   the NameError was swallowed by the function's own try/except, so the
   cleanup silently never deleted anything.
"""
def test_admin_move_voucher_reads_json_body(client, student_user, as_user):
    as_user(student_user)  # as_user overrides require_admin too
    r = client.post(
        "/api/v1/admin/internships/999999/vouchers/1/move",
        json={"target_internship_id": 5},
    )
    # Body must be parsed: unknown voucher → 404 from the handler,
    # never a 422 complaining that the "payload" query param is missing.
    # (main.py's global @exception_handler(404) rewrites every 404 detail to
    # "Endpoint not found", so only the status code can be asserted here.)
    assert r.status_code == 404, r.text


def test_require_role_builds_a_dependency():
    from app.services.auth_service import AuthService

    checker = AuthService.require_role(["admin"])  # NameError before the fix
    assert callable(checker)


# NOTE: no test for secure_upload.clean_old_files — app/core/secure_upload.py
# imports python-magic at module level, which hangs at import time on Windows
# without a libmagic DLL (Magic(...).load() in magic/compat.py). The module is
# not imported anywhere in the app; the missing `timedelta` import was fixed
# by inspection (pyflakes) and verified with `python -c "import ast; ..."`.
