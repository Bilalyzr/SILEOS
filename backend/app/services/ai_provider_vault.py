"""Encrypted credential vault and resilient provider dispatch for Sasha AI."""
from __future__ import annotations

import base64
import hashlib
import hmac
import os
import re
from dataclasses import dataclass
from datetime import datetime, timezone
from time import perf_counter
from typing import Iterable

import httpx
from cryptography.fernet import Fernet, InvalidToken
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.database import SessionLocal
from app.models.ai_provider import AiProviderCredential
from app.models.ai_provider_usage import AiProviderUsageEvent


GLM_URL = "https://open.bigmodel.cn/api/paas/v4/chat/completions"
GEMINI_URL = "https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
PROVIDERS = {"glm", "gemini"}
DEFAULT_MODELS = {"glm": "glm-5.2", "gemini": "gemini-2.5-flash"}
_MODEL_RE = re.compile(r"^[A-Za-z0-9._-]{2,100}$")


class ProviderConfigurationError(RuntimeError):
    pass


class ProviderRequestError(RuntimeError):
    """A user-actionable provider failure that contains no credential data."""


def _clean_provider_message(value: object) -> str:
    message = " ".join(str(value or "").split())[:220]
    # Defensive redaction in case a provider ever echoes an auth header.
    message = re.sub(
        r"(?i)(authorization|api[_ -]?key|bearer)\s*[:=]?\s*[^\s,;]+",
        r"\1 [redacted]",
        message,
    )
    return message


def _provider_http_error(provider: str, response: httpx.Response) -> ProviderRequestError:
    status_code = response.status_code
    message = ""
    code = ""
    try:
        payload = response.json()
        error = payload.get("error") if isinstance(payload, dict) else None
        if isinstance(error, dict):
            message = _clean_provider_message(error.get("message"))
            code = _clean_provider_message(error.get("code") or error.get("status"))
        elif isinstance(payload, dict):
            message = _clean_provider_message(payload.get("message") or payload.get("msg"))
            code = _clean_provider_message(payload.get("code"))
    except Exception:
        message = ""

    if status_code == 400:
        action = "The selected model or request is unsupported. Choose a listed model."
    elif status_code == 401:
        action = "The API key was rejected. Replace it with a valid server API key."
    elif status_code == 403:
        action = "This key does not have access to the selected model or endpoint."
    elif status_code == 404:
        action = "The selected model or provider endpoint was not found."
    elif status_code == 402:
        action = "Provider billing or credits are required for this request."
    elif status_code == 429:
        action = "The provider rate limit or quota was reached. Try a fallback key or review quota."
    elif status_code >= 500:
        action = "The provider is temporarily unavailable. Sasha will try the next active key."
    else:
        action = "The provider rejected the request."
    suffix = f" Provider detail: {message}" if message else ""
    code_suffix = f" ({code})" if code else ""
    return ProviderRequestError(
        f"{provider.title()} HTTP {status_code}{code_suffix}: {action}{suffix}"
    )


def provider_error_detail(provider: str, exc: Exception) -> str:
    if isinstance(exc, ProviderRequestError):
        return str(exc)
    if isinstance(exc, httpx.TimeoutException):
        return f"{provider.title()} timed out. Check outbound HTTPS access and try again."
    if isinstance(exc, httpx.ConnectError):
        return f"Could not connect to {provider.title()}. Check DNS, firewall, proxy, and outbound HTTPS access."
    if isinstance(exc, ProviderConfigurationError):
        return str(exc)
    return f"{provider.title()} request failed unexpectedly ({type(exc).__name__})."


@dataclass(frozen=True)
class ProviderCandidate:
    provider: str
    api_key: str
    model: str
    credential_id: int | None = None
    label: str = "Environment fallback"


def _master_secret() -> bytes:
    settings = get_settings()
    value = (os.environ.get("AI_CREDENTIAL_ENCRYPTION_KEY") or settings.SECRET_KEY).encode("utf-8")
    return hashlib.sha256(value).digest()


def _fernet() -> Fernet:
    return Fernet(base64.urlsafe_b64encode(_master_secret()))


def encrypt_api_key(api_key: str) -> str:
    value = api_key.strip()
    if len(value) < 8:
        raise ValueError("API key must contain at least 8 characters")
    return _fernet().encrypt(value.encode("utf-8")).decode("ascii")


def decrypt_api_key(ciphertext: str) -> str:
    try:
        return _fernet().decrypt(ciphertext.encode("ascii")).decode("utf-8")
    except (InvalidToken, ValueError) as exc:
        raise ProviderConfigurationError(
            "Stored credential cannot be decrypted. Verify AI_CREDENTIAL_ENCRYPTION_KEY."
        ) from exc


def key_fingerprint(api_key: str) -> str:
    return hmac.new(_master_secret(), api_key.strip().encode("utf-8"), hashlib.sha256).hexdigest()


def key_hint(api_key: str) -> str:
    value = api_key.strip()
    return f"•••• {value[-4:]}"


def _safe_model(provider: str, model: str | None) -> str:
    selected = (model or DEFAULT_MODELS[provider]).strip()
    if not _MODEL_RE.fullmatch(selected):
        raise ProviderConfigurationError("Provider model name contains unsupported characters")
    return selected


def _database_candidates() -> list[ProviderCandidate]:
    db = SessionLocal()
    try:
        rows = (
            db.query(AiProviderCredential)
            .filter(AiProviderCredential.is_active.is_(True))
            .order_by(AiProviderCredential.priority.asc(), AiProviderCredential.id.asc())
            .all()
        )
        candidates = []
        for row in rows:
            if row.provider not in PROVIDERS:
                continue
            try:
                candidates.append(ProviderCandidate(
                    provider=row.provider,
                    api_key=decrypt_api_key(row.key_ciphertext),
                    model=_safe_model(row.provider, row.model),
                    credential_id=row.id,
                    label=row.label,
                ))
            except ProviderConfigurationError:
                # A key encrypted with an old master secret must not prevent
                # other healthy credentials or environment fallbacks running.
                continue
        return candidates
    except SQLAlchemyError:
        db.rollback()
        return []
    finally:
        db.close()


def _environment_candidates() -> Iterable[ProviderCandidate]:
    glm_key = (os.environ.get("GLM_API_KEY") or os.environ.get("ZHIPUAI_API_KEY") or "").strip()
    if glm_key:
        yield ProviderCandidate("glm", glm_key, _safe_model("glm", os.environ.get("GLM_MODEL")))
    gemini_key = (os.environ.get("GEMINI_API_KEY") or "").strip()
    if gemini_key:
        yield ProviderCandidate("gemini", gemini_key, _safe_model("gemini", os.environ.get("GEMINI_MODEL")))


def configured_candidates() -> list[ProviderCandidate]:
    candidates = [*_database_candidates(), *_environment_candidates()]
    seen: set[tuple[str, str]] = set()
    unique: list[ProviderCandidate] = []
    for candidate in candidates:
        marker = (candidate.provider, hashlib.sha256(candidate.api_key.encode()).hexdigest())
        if marker not in seen:
            seen.add(marker)
            unique.append(candidate)
    return unique


def has_configured_provider() -> bool:
    try:
        return bool(configured_candidates())
    except ProviderConfigurationError:
        return False


def call_provider(candidate: ProviderCandidate, system: str, prompt: str, max_tokens: int = 4096) -> str:
    if candidate.provider == "glm":
        response = httpx.post(
            GLM_URL,
            headers={"Authorization": f"Bearer {candidate.api_key}", "Content-Type": "application/json"},
            json={
                "model": candidate.model,
                "max_tokens": max_tokens,
                "messages": [
                    {"role": "system", "content": system},
                    {"role": "user", "content": prompt},
                ],
            },
            timeout=90.0,
        )
        if response.status_code != 200:
            raise _provider_http_error("glm", response)
        choices = response.json().get("choices") or []
        text = choices[0].get("message", {}).get("content", "") if choices else ""
    elif candidate.provider == "gemini":
        response = httpx.post(
            GEMINI_URL.format(model=candidate.model),
            headers={"x-goog-api-key": candidate.api_key, "Content-Type": "application/json"},
            json={
                "systemInstruction": {"parts": [{"text": system}]},
                "contents": [{"role": "user", "parts": [{"text": prompt}]}],
                "generationConfig": {"maxOutputTokens": max_tokens},
            },
            timeout=90.0,
        )
        if response.status_code != 200:
            raise _provider_http_error("gemini", response)
        candidates = response.json().get("candidates") or []
        parts = candidates[0].get("content", {}).get("parts", []) if candidates else []
        text = "".join(str(part.get("text", "")) for part in parts)
    else:
        raise ProviderConfigurationError(f"Unsupported AI provider: {candidate.provider}")
    if not text.strip():
        raise RuntimeError(f"{candidate.provider.title()} returned an empty response")
    return text.strip()


def _safe_feature(feature: str | None) -> str:
    value = (feature or "").strip()
    return value[:80] if value else "general"


def _record_attempt(
    credential_id: int | None,
    provider: str,
    model: str,
    feature: str | None,
    success: bool,
    latency_ms: int | None,
    error: str = "",
) -> None:
    db = SessionLocal()
    try:
        db.add(AiProviderUsageEvent(
            credential_id=credential_id,
            provider=provider,
            model=model,
            feature=_safe_feature(feature),
            success=1 if success else 0,
            latency_ms=latency_ms,
            error=error[:300],
        ))
        db.commit()
    except SQLAlchemyError:
        db.rollback()
    finally:
        db.close()


def _record_result(credential_id: int | None, success: bool, error: str = "", tested: bool = False) -> None:
    if credential_id is None:
        return
    db = SessionLocal()
    try:
        row = db.query(AiProviderCredential).filter(AiProviderCredential.id == credential_id).first()
        if not row:
            return
        now = datetime.now(timezone.utc)
        row.last_used_at = now
        if tested:
            row.last_tested_at = now
        if success:
            row.health_status = "healthy"
            row.failure_count = 0
            row.last_error = ""
        else:
            row.failure_count = (row.failure_count or 0) + 1
            row.health_status = "failing" if row.failure_count >= 3 else "degraded"
            row.last_error = error[:300]
        db.commit()
    except SQLAlchemyError:
        db.rollback()
    finally:
        db.close()


def generate_with_failover(system: str, prompt: str, max_tokens: int = 4096, feature: str | None = None) -> str:
    candidates = configured_candidates()
    if not candidates:
        raise ProviderConfigurationError(
            "AI is not configured. Add an active GLM or Gemini key in Admin → AI Provider Vault."
        )
    failures: list[str] = []
    for candidate in candidates:
        started_at = perf_counter()
        try:
            result = call_provider(candidate, system, prompt, max_tokens)
            latency_ms = int((perf_counter() - started_at) * 1000)
            _record_attempt(
                candidate.credential_id,
                candidate.provider,
                candidate.model,
                feature,
                True,
                latency_ms,
            )
            _record_result(candidate.credential_id, True)
            return result
        except Exception as exc:
            latency_ms = int((perf_counter() - started_at) * 1000)
            safe_error = provider_error_detail(candidate.provider, exc)
            failures.append(f"{candidate.label}: {safe_error}")
            _record_attempt(
                candidate.credential_id,
                candidate.provider,
                candidate.model,
                feature,
                False,
                latency_ms,
                safe_error,
            )
            _record_result(candidate.credential_id, False, safe_error)
    joined = " | ".join(failures)
    raise RuntimeError(
        f"All configured AI providers failed ({len(failures)} attempted). {joined}"
    )


def test_credential(db: Session, credential: AiProviderCredential) -> str:
    candidate = ProviderCandidate(
        provider=credential.provider,
        api_key=decrypt_api_key(credential.key_ciphertext),
        model=_safe_model(credential.provider, credential.model),
        credential_id=credential.id,
        label=credential.label,
    )
    now = datetime.now(timezone.utc)
    try:
        call_provider(candidate, "Reply with only the word READY.", "Provider health check", max_tokens=12)
        credential.health_status = "healthy"
        credential.failure_count = 0
        credential.last_error = ""
        outcome = "healthy"
    except Exception as exc:
        credential.failure_count = (credential.failure_count or 0) + 1
        credential.health_status = "failing" if credential.failure_count >= 3 else "degraded"
        credential.last_error = provider_error_detail(credential.provider, exc)[:300]
        outcome = credential.health_status
    credential.last_tested_at = now
    credential.last_used_at = now
    db.commit()
    db.refresh(credential)
    return outcome
