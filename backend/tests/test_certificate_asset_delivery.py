"""Certificate asset delivery: payload size and CDN-cacheable URLs.

Both regressions these cover were measured on production:

* the on-screen certificate was a 1,356,773-byte PNG (1800x1158). The same
  render as WebP is ~100KB — the preview was shipping ~13x the bytes it
  needed to;
* every certificate asset is served from an extensionless
  `/api/v1/certificates/...` route. Cloudflare's default cache is keyed on
  file extension, so all four sampled requests came back
  `cf-cache-status: DYNAMIC` — the origin's `Cache-Control: max-age=86400`
  never took effect at the edge and every view/download was a full origin
  fetch. The identical bytes under `/certificate-files/*.png` cache fine.

The fix is to let the asset routes carry a real extension, so the URL the
browser requests ends in `.webp` / `.png` / `.pdf`.

Run inside the backend container:

    docker exec sasha-backend-blue python -m pytest tests/test_certificate_asset_delivery.py -q
"""

import io
import pathlib
import sys
import types

import pytest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

from app.routers.certificates import split_asset_ext, negotiate_image_format  # noqa: E402
from app.services.certificate_service import CertificateService  # noqa: E402


def _issued(**kw):
    cert = types.SimpleNamespace(
        id=11,
        certificate_id=1,
        secure_certificate_id="15374834CD54BCB30989",
        certificate_hash="8e0efeb308db0e0e615d8f24ee998730",
    )
    cert.__dict__.update(kw)
    return cert


# ---------------------------------------------------------------------------
# URL extensions — what makes the response cacheable at the CDN edge
# ---------------------------------------------------------------------------

HASH = "8e0efeb308db0e0e615d8f24ee998730"


@pytest.mark.parametrize(
    "raw, allowed, expected",
    [
        (f"{HASH}.webp", (".webp", ".png"), (HASH, ".webp")),
        (f"{HASH}.png", (".webp", ".png"), (HASH, ".png")),
        (f"{HASH}.pdf", (".pdf",), (HASH, ".pdf")),
        # Upper-case extension still resolves to the canonical lower-case one.
        (f"{HASH}.PNG", (".webp", ".png"), (HASH, ".png")),
        # No extension: the existing links keep working, unchanged.
        (HASH, (".webp", ".png"), (HASH, None)),
        # An extension we do not serve is part of the hash, not a format.
        (f"{HASH}.gif", (".webp", ".png"), (f"{HASH}.gif", None)),
    ],
)
def test_split_asset_ext(raw, allowed, expected):
    assert split_asset_ext(raw, allowed) == expected


def test_hash_lookup_is_unaffected_by_the_extension():
    """The DB lookup must use the bare hash, or the suffixed URL 404s."""
    bare, _ = split_asset_ext(f"{HASH}.webp", (".webp", ".png"))
    assert bare == HASH


# ---------------------------------------------------------------------------
# Format negotiation — browsers get WebP, crawlers keep PNG
# ---------------------------------------------------------------------------

CHROME_ACCEPT = "image/avif,image/webp,image/apng,image/svg+xml,image/*,*/*;q=0.8"
LINKEDIN_ACCEPT = "*/*"


def test_explicit_extension_wins_over_the_accept_header():
    assert negotiate_image_format(".png", CHROME_ACCEPT) == "png"
    assert negotiate_image_format(".webp", LINKEDIN_ACCEPT) == "webp"


def test_browser_that_accepts_webp_gets_webp():
    assert negotiate_image_format(None, CHROME_ACCEPT) == "webp"


def test_crawler_without_webp_support_gets_png():
    """LinkedIn renders og:image server-side and does not advertise WebP.

    Serving it WebP would break every share preview, so a client that does
    not ask for WebP must keep getting the PNG.
    """
    assert negotiate_image_format(None, LINKEDIN_ACCEPT) == "png"
    assert negotiate_image_format(None, "") == "png"
    assert negotiate_image_format(None, None) == "png"


# ---------------------------------------------------------------------------
# Payload size — the reason the preview was slow
# ---------------------------------------------------------------------------


def _real_render_png() -> bytes:
    """An actual cached certificate render.

    A synthetic image proves nothing here: how well WebP beats PNG depends
    entirely on the content, and the claim under test is about the real
    certificate design — smooth gradients, a photographic seal, large flat
    areas — which is exactly what PNG stores badly and WebP stores well.
    """
    cache_dir = pathlib.Path(CertificateService._html_pdf_cache_dir)
    renders = sorted(cache_dir.glob("cert_img_*.png"))
    if not renders:
        pytest.skip(f"no cached certificate render under {cache_dir} to measure")
    return renders[0].read_bytes()


def test_webp_conversion_is_dramatically_smaller_than_the_png():
    png = _real_render_png()
    webp = CertificateService.png_to_webp(png)

    assert webp, "conversion returned nothing"
    assert webp[:4] == b"RIFF" and webp[8:12] == b"WEBP", "not a WebP payload"
    # Measured on production: 1,356,773 bytes PNG -> 100,728 bytes WebP, 13.5x.
    # Assert only a 4x floor so a future template change can shift the ratio
    # without a spurious failure — but anything under that is not worth the
    # second encode and means something regressed.
    assert len(webp) * 4 < len(png), (
        f"WebP {len(webp)} bytes vs PNG {len(png)} bytes — only "
        f"{len(png) / len(webp):.1f}x, expected at least 4x"
    )


def test_webp_conversion_preserves_the_certificate_dimensions():
    from PIL import Image

    png = _real_render_png()
    webp = CertificateService.png_to_webp(png)

    assert Image.open(io.BytesIO(webp)).size == Image.open(io.BytesIO(png)).size


def test_png_to_webp_returns_none_on_garbage_rather_than_raising():
    """A conversion failure must degrade to serving the PNG, not 500."""
    assert CertificateService.png_to_webp(b"not an image") is None


def test_webp_cache_path_sits_beside_the_png_and_is_id_scoped():
    cert = _issued()
    png_path = CertificateService._png_cache_path(cert)
    webp_path = CertificateService._webp_cache_path(cert)

    assert webp_path.endswith("cert_img_15374834CD54BCB30989.webp")
    assert pathlib.Path(webp_path).parent == pathlib.Path(png_path).parent


def test_webp_cache_path_strips_non_alphanumerics_from_the_id():
    """Same hardening as the PNG path — the id reaches the filesystem."""
    cert = _issued(secure_certificate_id="../../etc/passwd")
    webp_path = CertificateService._webp_cache_path(cert)

    assert ".." not in webp_path
    assert webp_path.endswith("cert_img_etcpasswd.webp")
