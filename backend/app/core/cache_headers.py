"""Anon-only edge-cache headers for public catalog endpoints.

Authenticated requests carry per-user data (ownership flags, entitlements)
baked into the response body, so they must never be cached at a shared edge.
Anonymous requests to the same route are identical for every caller and are
safe to cache with a stale-while-revalidate window.
"""
from fastapi import Request, Response


def apply_public_cache(request: Request, response: Response, *,
                       s_maxage: int, swr: int) -> None:
    """Anon requests → edge-cacheable; authed → private. Callers pass the
    route's Request and Response (FastAPI injects both when declared)."""
    response.headers["Vary"] = "Authorization"
    if request.headers.get("authorization"):
        response.headers["Cache-Control"] = "private, no-store"
    else:
        response.headers["Cache-Control"] = (
            f"public, s-maxage={s_maxage}, stale-while-revalidate={swr}"
        )
