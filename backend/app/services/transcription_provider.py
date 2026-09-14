"""Self-hosted ASR subprocess. No audio uploads and no model downloads at runtime."""
import json
import os
from pathlib import Path
import subprocess
import sys
from app.core.config import get_settings

TIMEOUT = 3600


def configuration():
    settings = get_settings()
    python = settings.TRANSCRIPTION_PYTHON or sys.executable
    model = settings.TRANSCRIPTION_MODEL_PATH
    enabled = settings.TRANSCRIPTION_PROVIDER == "self_hosted"
    ready = enabled and Path(python).is_file() and bool(model) and (Path(model) / "model.bin").is_file()
    return {"provider": "self_hosted", "configured": ready,
            "note": "Recordings stay on this server." if ready else "Install the local transcription runtime and model; see docs/RECORDING_LESSONS.md."}


def transcribe(path, language_hint="auto"):
    if not configuration()["configured"]:
        raise ValueError("Local transcription is not configured. Ask an administrator to install the runtime and model.")
    runner = Path(__file__).resolve().parents[2] / "scripts" / "transcribe_local.py"
    settings = get_settings()
    env = {**os.environ, "TRANSCRIPTION_DEVICE": settings.TRANSCRIPTION_DEVICE, "TRANSCRIPTION_COMPUTE_TYPE": settings.TRANSCRIPTION_COMPUTE_TYPE, "HF_HUB_OFFLINE": "1", "HF_HUB_DISABLE_TELEMETRY": "1"}
    try:
        result = subprocess.run([(settings.TRANSCRIPTION_PYTHON or sys.executable), str(runner),
                                 str(path), settings.TRANSCRIPTION_MODEL_PATH, language_hint],
                                capture_output=True, text=True, encoding="utf-8", timeout=TIMEOUT, env=env,
                                creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
    except subprocess.TimeoutExpired:
        raise ValueError("Transcription exceeded one hour. Split the recording or use a faster local model.") from None
    if result.returncode:
        # Runtime stderr can contain local paths. Keep it out of user responses.
        raise ValueError("Local transcription failed. Check the runtime, model and recording, then retry.")
    return json.loads(result.stdout)
