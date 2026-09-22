from types import SimpleNamespace

import pytest


def test_admin_can_add_multiple_masked_provider_keys(client, make_user, as_user, db):
    admin = make_user(role="admin")
    as_user(admin)
    headers = {}

    first = client.post("/api/v1/ai/providers", headers=headers, json={
        "label": "Primary GLM",
        "provider": "glm",
        "api_key": "glm-secret-one-1234",
        "model": "glm-4.5",
        "priority": 10,
    })
    second = client.post("/api/v1/ai/providers", headers=headers, json={
        "label": "Gemini fallback",
        "provider": "gemini",
        "api_key": "gemini-secret-two-9876",
        "model": "gemini-2.5-flash",
        "priority": 100,
    })

    assert first.status_code == 201, first.text
    assert second.status_code == 201, second.text
    rows = client.get("/api/v1/ai/providers", headers=headers)
    assert rows.status_code == 200
    body = rows.json()
    assert [item["label"] for item in body] == ["Primary GLM", "Gemini fallback"]
    assert body[0]["key_hint"] == "•••• 1234"
    assert body[1]["key_hint"] == "•••• 9876"
    assert "secret" not in rows.text

    from app.models.ai_provider import AiProviderCredential
    stored = db.query(AiProviderCredential).order_by(AiProviderCredential.priority).all()
    assert "glm-secret-one-1234" not in stored[0].key_ciphertext
    assert "gemini-secret-two-9876" not in stored[1].key_ciphertext


def test_duplicate_provider_key_is_rejected(client, make_user, as_user):
    admin = make_user(role="admin")
    as_user(admin)
    headers = {}
    payload = {"label": "Key A", "provider": "glm", "api_key": "same-provider-key-1234"}
    assert client.post("/api/v1/ai/providers", headers=headers, json=payload).status_code == 201
    payload["label"] = "Key B"
    response = client.post("/api/v1/ai/providers", headers=headers, json=payload)
    assert response.status_code == 409


def test_students_cannot_read_or_write_provider_keys(client, make_user, auth_headers):
    student = make_user(role="student")
    headers = auth_headers(student.user_email, student._test_password)
    assert client.get("/api/v1/ai/providers", headers=headers).status_code == 403
    assert client.post("/api/v1/ai/providers", headers=headers, json={
        "label": "No access", "provider": "glm", "api_key": "blocked-key-1234",
    }).status_code == 403


def test_provider_dispatch_fails_over_in_priority_order(monkeypatch):
    from app.services import ai_provider_vault as vault

    candidates = [
        vault.ProviderCandidate("glm", "first-key", "glm-4.5", credential_id=1, label="primary"),
        vault.ProviderCandidate("gemini", "second-key", "gemini-2.5-flash", credential_id=2, label="fallback"),
    ]
    attempts = []
    recorded = []

    monkeypatch.setattr(vault, "configured_candidates", lambda: candidates)
    monkeypatch.setattr(vault, "_record_result", lambda credential_id, success, error="", tested=False: recorded.append((credential_id, success)))

    def fake_call(candidate, system, prompt, max_tokens=4096):
        attempts.append(candidate.label)
        if candidate.label == "primary":
            raise RuntimeError("quota")
        return "fallback answer"

    monkeypatch.setattr(vault, "call_provider", fake_call)
    assert vault.generate_with_failover("system", "prompt") == "fallback answer"
    assert attempts == ["primary", "fallback"]
    assert recorded == [(1, False), (2, True)]


def test_gemini_adapter_uses_header_without_leaking_key(monkeypatch):
    from app.services import ai_provider_vault as vault

    captured = {}

    def fake_post(url, **kwargs):
        captured.update(url=url, **kwargs)
        return SimpleNamespace(
            status_code=200,
            json=lambda: {"candidates": [{"content": {"parts": [{"text": "READY"}]}}]},
        )

    monkeypatch.setattr(vault.httpx, "post", fake_post)
    candidate = vault.ProviderCandidate("gemini", "private-key-1234", "gemini-2.5-flash")
    assert vault.call_provider(candidate, "system", "prompt", 24) == "READY"
    assert captured["headers"]["x-goog-api-key"] == "private-key-1234"
    assert "private-key-1234" not in captured["url"]
    assert captured["json"]["generationConfig"]["maxOutputTokens"] == 24


def test_provider_error_preserves_safe_actionable_upstream_detail(monkeypatch):
    from app.services import ai_provider_vault as vault

    def fake_post(_url, **_kwargs):
        return SimpleNamespace(
            status_code=400,
            json=lambda: {"error": {"code": "1211", "message": "Model glm-5.3 does not exist"}},
        )

    monkeypatch.setattr(vault.httpx, "post", fake_post)
    candidate = vault.ProviderCandidate("glm", "private-key-1234", "glm-5.3")
    with pytest.raises(vault.ProviderRequestError) as caught:
        vault.call_provider(candidate, "system", "prompt", 24)
    detail = str(caught.value)
    assert "HTTP 400" in detail
    assert "Choose a listed model" in detail
    assert "glm-5.3" in detail
    assert "private-key-1234" not in detail


def test_failover_error_names_each_provider_and_action(monkeypatch):
    from app.services import ai_provider_vault as vault

    monkeypatch.setattr(vault, "configured_candidates", lambda: [
        vault.ProviderCandidate("glm", "secret", "glm-5.2", label="Primary GLM"),
    ])
    monkeypatch.setattr(vault, "call_provider", lambda *_args, **_kwargs: (_ for _ in ()).throw(
        vault.ProviderRequestError("Glm HTTP 429: The provider rate limit or quota was reached."),
    ))
    with pytest.raises(RuntimeError) as caught:
        vault.generate_with_failover("system", "prompt")
    assert "Primary GLM" in str(caught.value)
    assert "quota" in str(caught.value)
