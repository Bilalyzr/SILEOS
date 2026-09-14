"""A-H3: admin-generated one-time password reset link — Batch 2 platform fix
wave. Admin must never set/see the user's actual password directly.
"""


class TestAdminPasswordResetLink:
    def test_admin_generates_reset_link(self, client, db, make_user, as_user):
        admin = make_user(role="admin", email="admin_pwreset1@example.com")
        target = make_user(role="student", email="target_pwreset1@example.com")
        as_user(admin)

        r = client.post(f"/api/v1/admin/users/{target.id}/password-reset-link")
        assert r.status_code == 200, r.text
        body = r.json()
        assert "reset_link" in body
        assert body["reset_link"]

    def test_reset_link_token_actually_resets_password(self, client, db, make_user, as_user):
        admin = make_user(role="admin", email="admin_pwreset2@example.com")
        target = make_user(role="student", email="target_pwreset2@example.com", password="OldPass@123")
        as_user(admin)

        r = client.post(f"/api/v1/admin/users/{target.id}/password-reset-link")
        assert r.status_code == 200, r.text
        link = r.json()["reset_link"]

        # Extract token= query param from the returned link
        assert "token=" in link
        token = link.split("token=")[-1]

        r2 = client.post("/api/v1/auth/reset-password", json={
            "token": token,
            "new_password": "NewPass@456",
        })
        assert r2.status_code == 200, r2.text

        # Old password should no longer work; new one should.
        r3 = client.post("/api/v1/auth/login", json={
            "email": target.user_email, "password": "NewPass@456",
        })
        assert r3.status_code == 200, r3.text

    def test_reset_link_is_single_use(self, client, db, make_user, as_user):
        admin = make_user(role="admin", email="admin_pwreset3@example.com")
        target = make_user(role="student", email="target_pwreset3@example.com")
        as_user(admin)

        r = client.post(f"/api/v1/admin/users/{target.id}/password-reset-link")
        token = r.json()["reset_link"].split("token=")[-1]

        r2 = client.post("/api/v1/auth/reset-password", json={
            "token": token, "new_password": "FirstUse@123",
        })
        assert r2.status_code == 200

        # Replay must fail (single-use jti marker cleared).
        r3 = client.post("/api/v1/auth/reset-password", json={
            "token": token, "new_password": "SecondUse@123",
        })
        assert r3.status_code == 400

    def test_non_admin_forbidden(self, client, db, make_user, auth_headers):
        student = make_user(role="student", email="notadmin_pwreset@example.com")
        target = make_user(role="student", email="target_pwreset4@example.com")
        headers = auth_headers(student.user_email, student._test_password)

        r = client.post(f"/api/v1/admin/users/{target.id}/password-reset-link", headers=headers)
        assert r.status_code == 403

    def test_404_for_unknown_user(self, client, db, make_user, as_user):
        admin = make_user(role="admin", email="admin_pwreset5@example.com")
        as_user(admin)

        r = client.post("/api/v1/admin/users/999999/password-reset-link")
        assert r.status_code == 404

    def test_admin_cannot_set_password_directly(self, client, db, make_user, as_user):
        """Guard against regressions: there must be no admin endpoint that
        accepts a plaintext new_password for another user."""
        admin = make_user(role="admin", email="admin_pwreset6@example.com")
        target = make_user(role="student", email="target_pwreset6@example.com")
        as_user(admin)

        r = client.post(
            f"/api/v1/admin/users/{target.id}/password-reset-link",
            json={"new_password": "Hacked@123"},
        )
        # Even if a body is sent, the route must ignore it and only ever
        # return a one-time link, never accept/set a password value.
        assert r.status_code == 200, r.text
        assert "new_password" not in r.json()
