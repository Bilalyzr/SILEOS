"""A source release must exclude private runtime data without removing features."""
import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location("release_packager", ROOT / "scripts/package_saas_release.py")
packager = importlib.util.module_from_spec(spec)
spec.loader.exec_module(packager)


def test_source_feature_directories_are_not_runtime_data():
    for relative in (
        "frontend/src/components/certificates/designer/CertificateDesignerEditor.tsx",
        "frontend/src/pages/ebooks/index.tsx",
        "backend/app/services/recordings/processor.py",
        "backend/app/models/invoices.py",
    ):
        assert packager.allowed(ROOT / relative), relative


def test_runtime_and_credentials_remain_excluded():
    for relative in (
        "backend/uploads/documents/private.pdf", "certificates/issued.pdf",
        "deploy/secrets/metrics-token", "backend/.env", "frontend/.env.local",
        "frontend/node_modules/example/index.js", "backend/test.db",
        "flutter_app/android/app/google-services.json",
    ):
        assert not packager.allowed(ROOT / relative), relative


def test_every_frontend_source_file_is_in_candidates():
    included = set(packager.candidates())
    for file in (ROOT / "frontend/src").rglob("*"):
        if file.is_file() and file.suffix in {".ts", ".tsx", ".css"}:
            assert file in included, file.relative_to(ROOT)
