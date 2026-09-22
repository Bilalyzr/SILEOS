"""Build one reviewed source snapshot for ZIP and Git; exclude runtime/private files.

Uses an explicit source allowlist, scans for known credential formats, writes
SHA256 manifests, and reads the finished ZIP back to verify every file.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import zipfile

ROOT = Path(__file__).resolve().parents[1]
SOURCE_DIRS = {"backend", "frontend", "flutter_app", "streaming-service", "code-judge-worker",
               "scripts", "docs", "deploy", "nginx", "database", "models", ".github"}
SKIP_DIRS = {".git", ".local", ".toolchains", ".venv", "venv", "node_modules", "__pycache__",
    "dist", "build", ".dart_tool", ".gradle", ".npm-cache", ".pytest_cache", ".astra-tools", "htmlcov"}
RUNTIME_DIRS = {
    "uploads", "certificates", "certificates_render_tmp", "invoices", "ebooks", "three_d", "backups",
    "recordings", "recordings_live", "transcription_models", "course_transfers", "secrets", "jitsi", "state"}
SKIP_NAMES = {".secret_key", ".jwt_secret", "youtube_cookies.txt", "env", "gitTok.md", "dec_2_changes.txt",
    "ts_errors.txt", "lms-ss.png", "lms-ss-t.png", "certificate.....png", "google-services.json", "GoogleService-Info.plist"}
SKIP_SUFFIXES = {".db", ".sqlite", ".sqlite3", ".dump", ".bak", ".backup", ".pem", ".key", ".p12", ".pfx",
    ".pyc", ".pyo", ".log", ".pid", ".mp4", ".webm", ".wav", ".mp3", ".zip", ".7z", ".gz"}
ROOT_NAMES = {".gitignore", ".dockerignore", ".env.example", "env.example", "pytest.ini", "pyproject.toml", "requirements.txt"}
ROOT_NAMES.update({"supervisord.conf", ".gitattributes", "LICENSE", "LICENSE.md", "LICENSE.txt", "NOTICE", "NOTICE.txt", "COPYING"})
PATTERNS = {
    "private-key": re.compile(rb"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----"),
    "github-token": re.compile(rb"\b(?:gh[pousr]_[A-Za-z0-9]{30,}|github_pat_[A-Za-z0-9_]{40,})\b"),
    "live-payment-key": re.compile(rb"\brzp_live_[A-Za-z0-9]{10,}\b"),
    "google-api-key": re.compile(rb"\bAIza[0-9A-Za-z_-]{30,}\b"),
    "provider-secret": re.compile(rb"\bsk-(?:proj-)?[A-Za-z0-9_-]{35,}\b"),
}


def skipped_directory(path):
    parts = path.relative_to(ROOT).parts
    if any(part in SKIP_DIRS for part in parts):
        return True
    # Runtime bind mounts, not source folders such as components/certificates.
    return bool(parts and (parts[0] in RUNTIME_DIRS or
        (parts[0] in {"backend", "streaming-service", "deploy"} and len(parts) > 1 and parts[1] in RUNTIME_DIRS)))


def allowed(file):
    relative = file.relative_to(ROOT)
    if skipped_directory(file.parent): return False
    name = file.name
    if name in SKIP_NAMES or name.startswith("_totp_"): return False
    if name.startswith(".env") and "example" not in name: return False
    if re.search(r"serviceAccount|firebase-adminsdk|firebase-service-account", name, re.I): return False
    if file.suffix.lower() in SKIP_SUFFIXES:
        if relative.as_posix() != "backend/seed_packs/cbse-supplied.zip": return False
    if len(relative.parts) == 1:
        return name in ROOT_NAMES or name.startswith("Dockerfile") or (
            file.suffix.lower() in {".md", ".yml", ".yaml", ".sh", ".ps1"}
            and not name.startswith(("2025-12-", "gitTok")))
    if relative.parts[0] not in SOURCE_DIRS: return False
    if relative.parts[0] == "docs" and relative.parts[1] in {"verification", "superpowers"}:
        # Historical reports/plans may contain copied credentials, shell history,
        # screenshots or obsolete implementation recipes. Current docs still ship.
        return False
    if relative.parts[0] == "database" and len(relative.parts) == 2 and name not in {"init.sql", "README.md"}:
        return False
    return True


def candidates():
    # Source templates only: never issued certificates or cached learner PDFs.
    template = ROOT / "certificates/template.html"
    if template.is_file() and not template.is_symlink():
        yield template
    for relative in ("certificates/templates", "certificates/assets", "certificates/thumbnails"):
        for asset in sorted((ROOT / relative).glob("*")):
            if asset.is_file() and not asset.is_symlink() and asset.suffix.lower() in {".html", ".js", ".png", ".svg", ".webp"}:
                yield asset
    for current, dirs, files in os.walk(ROOT):
        parent = Path(current)
        dirs[:] = sorted(d for d in dirs if not skipped_directory(parent / d) and not (parent / d).is_symlink()
                         and (parent != ROOT or d in SOURCE_DIRS))
        for name in sorted(files):
            file = parent / name
            if not file.is_symlink() and allowed(file): yield file


def build(version):
    dest = ROOT / "deliverables" / "release-source"
    dest.mkdir(parents=True, exist_ok=True)
    files, findings = [], []
    for file in candidates():
        relative = file.relative_to(ROOT).as_posix()
        read_path = Path("\\\\?\\" + str(file)) if os.name == "nt" else file
        data = read_path.read_bytes()
        # Match the checkout contract in .gitattributes and keep Linux shell
        # entrypoints runnable when the archive was assembled on Windows.
        if file.suffix.lower() in {".sh", ".conf", ".yml", ".yaml"} or file.name.startswith("Dockerfile") or file.name == ".env.deploy.example":
            data = data.replace(b"\r\n", b"\n")
        # Keys embedded in public frontend configuration must be reviewed too.
        for label, pattern in PATTERNS.items():
            matches = pattern.findall(data)
            # Exact synthetic redaction fixtures, not a broad tests-directory bypass.
            if relative in {"backend/tests/test_refunds.py", "scripts/package_saas_release.py"} and label == "live-payment-key":
                matches = [m for m in matches if m not in {b"rzp_live_AbCdEf123456", b"rzp_live_SECRET123"}]
            if matches: findings.append({"file": relative, "type": label})
        files.append((relative, data))
    scan = ROOT / ".local" / "release-secret-scan.json"
    scan.parent.mkdir(exist_ok=True)
    scan.write_text(json.dumps({"files": len(files), "findings": findings}, indent=2), encoding="utf-8")
    if findings:
        print(json.dumps({"blocked": "credential-pattern review", "findings": findings}, indent=2))
        raise SystemExit(2)
    # Never delete the workspace or an existing release snapshot. Stale files
    # are refused, so ZIP and Git input cannot silently diverge.
    expected = {relative for relative, _ in files}
    existing = {f.relative_to(dest).as_posix() for f in dest.rglob("*") if f.is_file()}
    stale = existing - expected - {"RELEASE_MANIFEST.json"}
    if stale: raise RuntimeError("Stale release snapshot files require review: " + ", ".join(sorted(stale)))
    manifest = {"version": version, "synthetic_data": "Run scripts/seed_saas_demo.py --seed; no database or passwords included",
        "files": [{"path": path, "bytes": len(data), "sha256": hashlib.sha256(data).hexdigest()} for path, data in files]}
    archive = ROOT / "deliverables" / f"SashaInfinity-SaaS-{version}.zip"
    with zipfile.ZipFile(archive, "w", zipfile.ZIP_DEFLATED, compresslevel=6) as out:
        for relative, data in files:
            target = dest / relative
            if os.name == "nt":
                # The downloaded workspace has a long directory name. Preserve
                # deep asset filenames instead of silently excluding them.
                target = Path("\\\\?\\" + str(target))
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(data)
            entry = zipfile.ZipInfo("SashaLMS/" + relative)
            entry.create_system = 3  # retain executable shell entrypoints on Linux extraction
            entry.external_attr = (0o100755 if relative.endswith(".sh") else 0o100644) << 16
            entry.compress_type = zipfile.ZIP_DEFLATED
            out.writestr(entry, data)
        raw = json.dumps(manifest, indent=2).encode()
        (dest / "RELEASE_MANIFEST.json").write_bytes(raw)
        out.writestr("SashaLMS/RELEASE_MANIFEST.json", raw)
    with zipfile.ZipFile(archive) as check:
        assert check.testzip() is None
        for entry in manifest["files"]:
            assert hashlib.sha256(check.read("SashaLMS/" + entry["path"])).hexdigest() == entry["sha256"]
            if entry["path"].endswith(".sh"):
                assert (check.getinfo("SashaLMS/" + entry["path"]).external_attr >> 16) & 0o111
    digest = hashlib.sha256(archive.read_bytes()).hexdigest()
    archive.with_suffix(".sha256").write_text(digest + "  " + archive.name + "\n", encoding="utf-8")
    print(json.dumps({"archive": str(archive), "source": str(dest), "files": len(files),
        "sha256": digest, "bytes": archive.stat().st_size, "verified": True}, indent=2))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--version", default="2026-09-14-runtime-rc1")
    args = parser.parse_args()
    if not re.fullmatch(r"[a-zA-Z0-9.-]{1,80}", args.version): parser.error("Invalid release version")
    build(args.version)
