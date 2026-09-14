"""Run with python -m app.workers.recording_lessons [--once]. Uses backend DB configuration."""
import argparse
import logging
import time
from app.core.database import SessionLocal
from app import models
assert models.RecordingLesson.__tablename__ == "recording_lessons"
from app.services.recording_lesson_service import run_one
from app.services.operations_service import heartbeat


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--once", action="store_true")
    args = parser.parse_args()
    while True:
        try:
            heartbeat("recording_worker", "processing")
            worked = run_one(SessionLocal)
            heartbeat("recording_worker", "ok")
        except Exception:
            logging.exception("Recording worker failed; will retry polling")
            worked = False
            heartbeat("recording_worker", "error")
        if args.once:
            break
        if not worked:
            time.sleep(10)


if __name__ == "__main__":
    main()
