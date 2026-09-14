def test_client_boots(client):
    r = client.get("/health")
    assert r.status_code == 200


def test_make_user_and_login(client, make_user, auth_headers):
    u = make_user(role="student", email="smoke@example.com")
    h = auth_headers("smoke@example.com")
    assert "Authorization" in h
