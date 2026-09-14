# Recording lessons

## Instructor workflow

Content Studio > Recording Lessons (or Past classes > Create lesson) lists completed classes the assigned instructor can edit.

1. Choose automatic language detection, English or Tamil, and queue transcription. New finalizer ingests also queue work automatically after the upload commits.
2. The separate local worker produces timestamped segments. Search, jump to signed recording playback, correct transcript text, edit notes, chapter titles/times and concepts. Initial notes are extracts, not a claimed semantic summary; initial chapter boundaries are roughly three minutes.
3. Save corrections, confirm review, and create the draft lesson. It appears in the existing course editor with source `class_report:<id>` and chapter links. This action never publishes.
4. Optionally create literal excerpt questions in Assessment Studio. They remain unpublished and need that studio's review and publication process. Creation is idempotent. Existing assessment drafts are independent; later transcript edits do not silently rewrite them.
5. Publish the lesson in the course editor. Published lessons with concept links become eligible for the existing planner; creating notes never awards progress, grades or mastery.

The reader at `/recordings/:classId` checks active/completed enrollment and both course and lesson publication on every request. Assigned course editors can preview private work. The reader never returns local paths, private processing errors or question keys. Media still uses the existing signed, enrollment-gated Bunny recording endpoint. If media has expired or signing is not configured, the transcript and notes remain readable. No unsigned playback fallback is introduced.

## Self-hosted runtime

Python 3.9+; this implementation was exercised with Python 3.13 on Windows CPU. The ASR environment is separate so its native dependencies do not change the API environment. From the repository root:

```powershell
python -m venv .transcription-venv
.\.transcription-venv\Scripts\python.exe -m pip install -r backend/requirements-transcription.txt
.\.transcription-venv\Scripts\python.exe backend/scripts/install_transcription_model.py --model small --directory backend/transcription_models/small
```

Linux uses `.transcription-venv/bin/python` instead. The one-time installer downloads public multilingual model weights. Inference sets offline mode, uses an explicit local path and does not upload recordings or invoke GLM. Model size is an operational choice: test real English/Tamil audio for accuracy and performance before production. The English smoke sample is not evidence of Tamil accuracy.

Configure these in **both the API and worker environments** (absolute paths):

```dotenv
TRANSCRIPTION_PROVIDER=self_hosted
TRANSCRIPTION_PYTHON=/srv/sasha/.transcription-venv/bin/python
TRANSCRIPTION_MODEL_PATH=/srv/sasha/backend/transcription_models/small
TRANSCRIPTION_DEVICE=cpu
TRANSCRIPTION_COMPUTE_TYPE=int8
JITSI_RECORDINGS_DIR=/recordings
```

Apply migration with the normal backend environment, then start a separate worker from `backend/`:

```sh
python -m alembic upgrade head
python -m app.workers.recording_lessons
```

`--once` processes at most one job for diagnostics/cron. Run the continuous worker under your service manager, with the same DB configuration and private recording mount as the API. It does not start implicitly in each API worker. Install the optional ASR venv/model in the container or host where this worker actually runs; host paths are not usable inside a container unless mounted. For the local Windows preview, `scripts/start-recording-worker.ps1` loads the existing development launch environment and starts just the recording worker.

## Reliability and limits

Migration 0023 adds `recording_lessons`; no existing table is altered. Source files must resolve inside JITSI_RECORDINGS_DIR and match the class's exact opaque room name. Public clients cannot supply filesystem paths. Existing ingests are unchanged; past recordings can be discovered when exactly one MP4 exists in the class room directory. Multiple files need the finalizer to register the intended source. Files removed from that mount cannot be transcribed by this implementation; it does not fetch arbitrary URLs or download from Bunny.

Queued work waits for a permanent class report and configured local model. Atomic version claims prevent duplicate workers. There is a one-hour subprocess timeout; interrupted jobs become failed after timeout plus two minutes and require explicit retry. UI shows queue/processing/failure/draft stages and attempt count, not fabricated percent completion. Ingest commits before the best-effort enqueue hook. Retrying an ingest cannot reset reviewed work.

Draft limits: 400,000 transcript characters, 20,000 segments, 20,000 note characters, 500 chapters, 20 concepts. Transcript corrections preserve original timestamps. A generated lesson freezes the recording workbench; further lesson text changes belong in the course editor. The recording reader preserves the reviewed source notes as a reference, while the curriculum lesson may subsequently be edited.

## Verification

Backend tests cover private drafts, publication/enrollment gates, stale versions, idempotent lesson and question creation, HTML escaping, source containment, deletion checks, worker recovery, invalid ASR output and migration parity. UI tests require saved corrections and explicit review, and cover retry and setup states. A real local speech sample produced four correctly timestamped English segments using the multilingual small model.

Provider API reference: [SYSTRAN faster-whisper](https://github.com/SYSTRAN/faster-whisper).
