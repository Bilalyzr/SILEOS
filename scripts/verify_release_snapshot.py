"""Read-only check that a staged Git snapshot matches every packaged source byte."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--git-dir", required=True, type=Path)
    args = parser.parse_args()
    source = ROOT / "deliverables/release-source"
    manifest = json.loads((source / "RELEASE_MANIFEST.json").read_text(encoding="utf-8"))
    command = ["git", "-C", str(source), f"--git-dir={args.git_dir.resolve()}", f"--work-tree={source}"]
    object_format = subprocess.check_output(command + ["rev-parse", "--show-object-format"]).strip().decode()
    assert object_format in {"sha1", "sha256"}, "Unsupported Git object format"
    records = subprocess.check_output(command + ["ls-files", "--stage", "-z"]).split(b"\0")
    staged = {}
    for record in records:
        if not record:
            continue
        metadata, path = record.split(b"\t", 1)
        mode, digest, stage = metadata.decode().split()
        assert stage == "0", "Unresolved Git index"
        staged[path.decode("utf-8")] = (mode, digest)
    expected = {item["path"]: item["sha256"] for item in manifest["files"]}
    expected["RELEASE_MANIFEST.json"] = None
    assert staged.keys() == expected.keys(), "Staged paths differ from release manifest"
    for relative, expected_sha in expected.items():
        file = source / relative
        if os.name == "nt":
            file = Path("\\\\?\\" + str(file))
        data = file.read_bytes()
        if expected_sha:
            assert hashlib.sha256(data).hexdigest() == expected_sha, f"Manifest mismatch: {relative}"
        blob = b"blob " + str(len(data)).encode() + b"\0" + data
        assert hashlib.new(object_format, blob).hexdigest() == staged[relative][1], f"Git byte mismatch: {relative}"
        if relative.endswith(".sh"):
            assert staged[relative][0] == "100755", f"Shell entrypoint is not executable: {relative}"
    print(json.dumps({"verified": True, "staged_files": len(staged), "manifest_files": len(manifest["files"])}))


if __name__ == "__main__":
    main()
