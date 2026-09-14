"""Certificate download-URL and template-resolution regressions.

Both bugs these cover shipped to production:

* every download served the frozen ReportLab PDF written at issue time, so a
  certificate downloaded after a template change showed the OLD design;
* every template in the picker rendered as the default design, because the
  template rows carried no slug for `resolve_template_path` to match.

Run inside the backend container:

    docker exec sasha-backend-blue python -m pytest tests/test_certificate_urls.py -q
"""

import pathlib
import sys
import types

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

from app.routers.certificates import (  # noqa: E402
    certificate_download_url,
    resolve_template_path,
    _DEFAULT_TEMPLATE_PATH,
    _TEMPLATES_DIR,
)


def _issued(**kw):
    cert = types.SimpleNamespace(
        id=11,
        certificate_id=1,
        secure_certificate_id="15374834CD54BCB30989",
        certificate_hash="8e0efeb308db0e0e615d8f24ee998730",
        certificate_download_url="/certificate-files/certificate_c240cf6d.pdf",
    )
    cert.__dict__.update(kw)
    return cert


class _FakeQuery:
    def __init__(self, row):
        self._row = row

    def filter(self, *_a, **_kw):
        return self

    def first(self):
        return self._row


class _FakeDB:
    """Stands in for a Session whose Certificate lookup returns `row`."""

    def __init__(self, row):
        self._row = row

    def query(self, *_a, **_kw):
        return _FakeQuery(self._row)


# --- download URL ----------------------------------------------------------


def test_download_url_uses_the_html_renderer_not_the_frozen_reportlab_pdf():
    cert = _issued()
    url = certificate_download_url(cert)

    # The trailing `.pdf` is load-bearing: Cloudflare's default cache is keyed
    # on the extension, and without one the edge never cached the download.
    assert url == (
        "/api/v1/certificates/download-pdf/"
        "15374834CD54BCB30989/8e0efeb308db0e0e615d8f24ee998730.pdf"
    )
    # The stored column is the bug — it must not leak through.
    assert "certificate_c240cf6d" not in url


def test_download_url_falls_back_to_the_stored_column_when_identity_missing():
    cert = _issued(secure_certificate_id="", certificate_hash="")
    assert certificate_download_url(cert) == "/certificate-files/certificate_c240cf6d.pdf"


def test_download_url_is_empty_when_there_is_nothing_to_serve():
    cert = _issued(secure_certificate_id="", certificate_hash="", certificate_download_url=None)
    assert certificate_download_url(cert) == ""


# --- template resolution ---------------------------------------------------


def test_template_with_a_slug_resolves_to_its_own_design_file():
    slug = "royal-navy"
    if not (_TEMPLATES_DIR / f"{slug}.html").is_file():
        import pytest

        pytest.skip(f"{slug}.html not present in this checkout")

    db = _FakeDB(types.SimpleNamespace(post_name=slug))
    assert resolve_template_path(db, _issued()) == _TEMPLATES_DIR / f"{slug}.html"


def test_template_without_a_slug_falls_back_to_the_default_design():
    db = _FakeDB(types.SimpleNamespace(post_name=""))
    assert resolve_template_path(db, _issued()) == _DEFAULT_TEMPLATE_PATH


def test_unknown_slug_falls_back_rather_than_breaking_rendering():
    db = _FakeDB(types.SimpleNamespace(post_name="no-such-design"))
    assert resolve_template_path(db, _issued()) == _DEFAULT_TEMPLATE_PATH
