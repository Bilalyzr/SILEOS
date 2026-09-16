"""Single LLM provider for the whole platform: Zhipu GLM (owner decision
2026-09-05 — no Anthropic). OpenAI-compatible chat-completions endpoint.

Env:
  GLM_API_KEY (or ZHIPUAI_API_KEY) — required; without it callers return
  an honest 503, never a faked answer.
  GLM_MODEL — optional; default "glm-4.5" (free-tier friendly alternative:
  "glm-4-flash").
"""
import os

import httpx

GLM_URL = "https://open.bigmodel.cn/api/paas/v4/chat/completions"
DEFAULT_MODEL = "glm-4.5"


def glm_api_key() -> str:
    return (os.environ.get("GLM_API_KEY")
            or os.environ.get("ZHIPUAI_API_KEY")
            or "").strip()


def glm_model() -> str:
    return os.environ.get("GLM_MODEL", DEFAULT_MODEL).strip() or DEFAULT_MODEL


def llm_configured() -> bool:
    return bool(glm_api_key())


def missing_key_detail(feature: str) -> str:
    return (f"{feature} is not configured: set GLM_API_KEY on the backend "
            f"to enable it. No answer is faked.")


def call_glm(system: str, prompt: str, api_key: str | None = None,
             model: str | None = None, max_tokens: int = 4096) -> str:
    """One synchronous GLM chat round trip -> assistant text.

    Module-level so tests monkeypatch it (no network in CI), same pattern
    the Anthropic version used.
    """
    key = api_key or glm_api_key()
    response = httpx.post(
        GLM_URL,
        headers={
            "Authorization": f"Bearer {key}",
            "Content-Type": "application/json",
        },
        json={
            "model": model or glm_model(),
            "max_tokens": max_tokens,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": prompt},
            ],
        },
        timeout=90.0,
    )
    if response.status_code != 200:
        raise RuntimeError(f"GLM API {response.status_code}: {response.text[:300]}")
    body = response.json()
    choices = body.get("choices") or []
    if not choices:
        raise RuntimeError("GLM API returned no choices")
    return choices[0].get("message", {}).get("content", "")
