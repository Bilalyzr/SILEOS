"""Standalone worker runtime; install requirements-transcription.txt in its own venv."""
import json
import os
import sys
from faster_whisper import WhisperModel


def main():
    path, model_path, language = sys.argv[1:]
    model = WhisperModel(model_path, device=os.getenv("TRANSCRIPTION_DEVICE", "cpu"),
                         compute_type=os.getenv("TRANSCRIPTION_COMPUTE_TYPE", "int8"),
                         cpu_threads=4, local_files_only=True)
    segments, info = model.transcribe(path, language=None if language == "auto" else language,
                                     beam_size=5, vad_filter=True, condition_on_previous_text=False)
    rows = [{"start": round(s.start, 2), "end": round(s.end, 2), "text": s.text.strip()}
            for s in segments if s.text.strip()]
    print(json.dumps({"language": info.language, "segments": rows,
                      "text": " ".join(s["text"] for s in rows)}, ensure_ascii=True))


if __name__ == "__main__":
    main()
