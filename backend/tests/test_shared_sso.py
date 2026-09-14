from app.core.security import create_refresh_token


def test_shared_session_cookie_can_restore_tokens(client, make_user):
    user = make_user(email="sso-user@example.com")
    refresh = create_refresh_token({"sub": str(user.id)})

    established = client.post("/api/v1/auth/sso", json={"refresh_token": refresh})
    assert established.status_code == 200
    assert established.json() == {"shared_session": True}
    assert "sasha_sso_refresh" in established.cookies

    restored = client.post("/api/v1/auth/refresh", json={})
    assert restored.status_code == 200
    assert restored.json()["user"]["id"] == user.id
    assert restored.json()["access_token"]


def test_shared_session_rejects_invalid_refresh_token(client):
    response = client.post("/api/v1/auth/sso", json={"refresh_token": "not-a-token"})
    assert response.status_code == 401
