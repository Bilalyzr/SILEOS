"""
Centralized CORS Configuration for SashaInfinity LMS

All CORS settings are managed here. Every FastAPI entry point
(main.py, main_simple.py, main_test.py, etc.) should call
setup_cors(app) instead of configuring CORSMiddleware inline.
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import get_settings


def setup_cors(app: FastAPI) -> None:
    """
    Apply the centralized CORS middleware to a FastAPI application.

    Origins are read from settings.CORS_ORIGINS (configured via the
    CORS_ORIGINS environment variable or defaults in config.py).
    """
    settings = get_settings()

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.CORS_ORIGINS,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS"],
        allow_headers=[
            "accept",
            "accept-language",
            "content-language",
            "content-type",
            "authorization",
            "x-api-key",
            "x-requested-with",
            "cache-control",
            "pragma",
            "expires",
            "x-build-timestamp",
        ],
        # Let browser JS read custom response headers (e.g. the blog list's
        # X-Total-Count used by the public blog page's pagination controls).
        expose_headers=["X-Total-Count"],
    )
