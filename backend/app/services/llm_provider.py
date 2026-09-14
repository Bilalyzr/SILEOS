"""Compatibility facade over Sasha's encrypted multi-provider key pool.

Existing callers keep using ``call_glm`` while dispatch can rotate across any
active GLM or Gemini credentials configured by an administrator. Environment
keys remain a final fallback for backwards-compatible deployments.
"""
import os

from app.services.ai_provider_vault import (
    ProviderCandidate,
    call_provider,
    generate_with_failover,
    has_configured_provider,
)

DEFAULT_MODEL = "glm-5.2"


def glm_api_key() -> str:
    return (os.environ.get("GLM_API_KEY")
            or os.environ.get("ZHIPUAI_API_KEY")
            or "").strip()


def glm_model() -> str:
    return os.environ.get("GLM_MODEL", DEFAULT_MODEL).strip() or DEFAULT_MODEL


def llm_configured() -> bool:
    return has_configured_provider()


def missing_key_detail(feature: str) -> str:
    return (f"{feature} is not configured. Add an active GLM or Gemini key in "
            "Admin → AI Provider Vault, or configure the GLM_API_KEY / "
            "GEMINI_API_KEY environment fallback. No answer is faked.")


def call_glm(system: str, prompt: str, api_key: str | None = None,
             model: str | None = None, max_tokens: int = 4096,
             *, feature: str | None = None) -> str:
    """One synchronous GLM chat round trip -> assistant text.

    Module-level so tests monkeypatch it (no network in CI), same pattern
    the Anthropic version used.
    """
    if api_key:
        return call_provider(
            ProviderCandidate("glm", api_key, model or glm_model()),
            system,
            prompt,
            max_tokens,
        )
    return generate_with_failover(system, prompt, max_tokens, feature)
