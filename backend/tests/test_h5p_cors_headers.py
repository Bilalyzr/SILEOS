"""Regression tests for review finding C1 — H5P asset CORS/MIME serving.

Background
----------
`frontend/public/h5p-player.html` is loaded inside an
`<iframe sandbox="allow-scripts">` WITHOUT `allow-same-origin`, so the browser
assigns the player document a unique OPAQUE origin. h5p-standalone does not
pull the package with `<script>`/`<img>` tags — it calls `fetch()` for
`h5p.json`, `content/content.json` and each library's descriptor.

A `fetch()` issued from an opaque origin carries `Origin: null` and is treated
by the browser as a CROSS-ORIGIN request even though the URL is same-site.
Without an `Access-Control-Allow-Origin` response header the browser discards
the response, so the H5P player never boots — the feature is dead on arrival.

These tests pin the server side of that contract:
  * `/uploads/h5p/**` carries ACAO:*, nosniff and `CSP: sandbox`
  * the REST of `/uploads/**` does NOT get a wildcard ACAO (the fix must stay
    scoped to the H5P subtree and never loosen general upload serving)
  * the MIME types h5p-standalone depends on resolve correctly on this host

`test_h5p_cors_browser.py` covers the same contract end-to-end in a real
headless browser.
"""
import json

import pytest


H5P_ASSET_HEADERS = {
    "access-control-allow-origin": "*",
    "x-content-type-options": "nosniff",
    "content-security-policy": "sandbox",
}


@pytest.fixture
def h5p_package(tmp_path_factory):
    """Materialize a minimal H5P package under the real uploads/h5p root that
    the app mounts, and clean it up afterwards."""
    from app.main import h5p_uploads_dir

    public_id = "0123456789abcdef0123456789abcdef"
    root = h5p_uploads_dir / public_id
    (root / "content").mkdir(parents=True, exist_ok=True)
    (root / "h5p.json").write_text(
        json.dumps({"title": "CORS probe", "mainLibrary": "H5P.Blanks"}),
        encoding="utf-8",
    )
    (root / "content" / "content.json").write_text(
        json.dumps({"text": "hello"}), encoding="utf-8"
    )
    (root / "lib.js").write_text("/* library */\n", encoding="utf-8")
    (root / "styles.css").write_text("body{}\n", encoding="utf-8")
    (root / "font.woff2").write_bytes(b"\x00wOF2stub")
    try:
        yield public_id
    finally:
        import shutil

        shutil.rmtree(root, ignore_errors=True)


@pytest.fixture
def plain_upload():
    """A file under /uploads that is NOT in the h5p subtree."""
    from app.main import uploads_dir

    path = uploads_dir / "_c1_probe_not_h5p.json"
    path.write_text(json.dumps({"ok": True}), encoding="utf-8")
    try:
        yield path.name
    finally:
        path.unlink(missing_ok=True)


def test_h5p_json_carries_cors_and_hardening_headers(client, h5p_package):
    """The DEFINITIVE sub-property: the file h5p-standalone fetch()es first
    must answer with ACAO:* or the opaque-origin player cannot read it."""
    resp = client.get(f"/uploads/h5p/{h5p_package}/h5p.json")

    assert resp.status_code == 200
    for header, expected in H5P_ASSET_HEADERS.items():
        assert resp.headers.get(header) == expected, (
            f"/uploads/h5p/*/h5p.json is missing {header}: {expected!r} — "
            "the sandboxed player's fetch() will be rejected by the browser"
        )


def test_h5p_nested_content_json_carries_cors_headers(client, h5p_package):
    """content/content.json is fetch()ed too — the headers must apply to the
    whole subtree, not just the top-level manifest."""
    resp = client.get(f"/uploads/h5p/{h5p_package}/content/content.json")

    assert resp.status_code == 200
    for header, expected in H5P_ASSET_HEADERS.items():
        assert resp.headers.get(header) == expected


def test_non_h5p_uploads_do_not_get_wildcard_acao(client, plain_upload):
    """The fix must stay scoped: ordinary uploads keep their previous
    behaviour and must NOT start advertising a wildcard ACAO."""
    resp = client.get(f"/uploads/{plain_upload}")

    assert resp.status_code == 200
    assert resp.headers.get("access-control-allow-origin") != "*"


def test_h5p_mount_precedence_over_general_uploads(client, h5p_package):
    """Starlette matches mounts in registration order — if the general
    /uploads mount were registered first it would swallow /uploads/h5p and
    silently strip the CORS headers."""
    resp = client.get(f"/uploads/h5p/{h5p_package}/lib.js")

    assert resp.status_code == 200
    assert resp.headers.get("access-control-allow-origin") == "*"


@pytest.mark.parametrize(
    "filename,expected_type",
    [
        ("h5p.json", "application/json"),
        ("lib.js", "text/javascript"),
        ("styles.css", "text/css"),
        ("font.woff2", "font/woff2"),
    ],
)
def test_h5p_assets_get_correct_mime_types(client, h5p_package, filename, expected_type):
    """Windows' mimetypes registry has no webfont entries (.woff/.woff2 both
    resolve to None), which is why app.main registers them explicitly. The
    others are asserted so a differently-configured host cannot regress them
    unnoticed."""
    resp = client.get(f"/uploads/h5p/{h5p_package}/{filename}")

    assert resp.status_code == 200
    assert resp.headers.get("content-type", "").split(";")[0].strip() == expected_type


def test_missing_h5p_asset_still_carries_headers(client):
    """The middleware wraps every response, 404s included — a bare 404 with
    no CORS header surfaces in the browser as an opaque CORS error rather
    than a clean 'not found', which makes the failure much harder to debug."""
    resp = client.get("/uploads/h5p/deadbeefdeadbeefdeadbeefdeadbeef/h5p.json")

    assert resp.status_code == 404
    assert resp.headers.get("access-control-allow-origin") == "*"
