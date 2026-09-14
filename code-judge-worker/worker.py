"""Lease Utporul submissions and execute them through a Judge0 sandbox.

This process never executes learner source itself. Judge0 receives one run per
test case with network disabled and the challenge's CPU/memory limits applied.
"""

from __future__ import annotations

import logging
import os
import time
from typing import Any

import httpx


logging.basicConfig(
    level=os.getenv("LOG_LEVEL", "INFO"),
    format="%(asctime)s %(levelname)s %(message)s",
)
logger = logging.getLogger("sasha-code-judge")

BACKEND_URL = os.getenv("BACKEND_INTERNAL_URL", "http://backend:8000/api/v1").rstrip("/")
JUDGE0_URL = os.getenv("JUDGE0_URL", "http://judge0-server:2358").rstrip("/")
RUNNER_TOKEN = os.getenv("CODE_RUNNER_TOKEN", "")
JUDGE0_AUTH_TOKEN = os.getenv("JUDGE0_AUTH_TOKEN", "")
POLL_SECONDS = max(0.25, float(os.getenv("CODE_RUNNER_POLL_SECONDS", "1")))
JUDGE_VERSION = os.getenv("CODE_RUNNER_VERSION", "judge0-worker-1.0")

LANGUAGE_PREFIXES = {
    "python": ("python (",),
    "javascript": ("javascript (node.js", "javascript ("),
    "typescript": ("typescript (",),
    "java": ("java (openjdk", "java ("),
    "cpp": ("c++ (gcc", "c++ ("),
    "c": ("c (gcc", "c ("),
}


def _headers() -> dict[str, str]:
    return {"X-Code-Runner-Token": RUNNER_TOKEN}


def _judge_headers() -> dict[str, str]:
    return {"X-Auth-Token": JUDGE0_AUTH_TOKEN} if JUDGE0_AUTH_TOKEN else {}


def _language_ids(client: httpx.Client) -> dict[str, int]:
    response = client.get(f"{JUDGE0_URL}/languages", headers=_judge_headers())
    response.raise_for_status()
    languages = response.json()
    mapping: dict[str, int] = {}
    for key, prefixes in LANGUAGE_PREFIXES.items():
        matches = [
            row
            for row in languages
            if any(str(row.get("name", "")).lower().startswith(prefix) for prefix in prefixes)
        ]
        if matches:
            # Judge0 ids are stable identifiers; choosing the highest matching
            # id selects the newest installed variant when several are present.
            mapping[key] = max(int(row["id"]) for row in matches)
    return mapping


def _wait_for_result(client: httpx.Client, token: str) -> dict[str, Any]:
    deadline = time.monotonic() + 30
    while time.monotonic() < deadline:
        response = client.get(
            f"{JUDGE0_URL}/submissions/{token}",
            params={"base64_encoded": "false", "fields": "stdout,stderr,compile_output,message,status,time,memory"},
            headers=_judge_headers(),
        )
        response.raise_for_status()
        result = response.json()
        if int(result.get("status", {}).get("id", 0)) not in (1, 2):
            return result
        time.sleep(0.2)
    raise TimeoutError("Judge0 submission did not finish before the worker deadline")


def _execute_case(
    client: httpx.Client,
    job: dict[str, Any],
    case: dict[str, Any],
    language_ids: dict[str, int],
) -> dict[str, Any]:
    language_id = language_ids.get(job["language"])
    if language_id is None:
        return {
            "test_case_id": case["id"],
            "status": "internal_error",
            "stderr": f"Language {job['language']} is not installed on the judge.",
        }
    limits = job["limits"]
    payload = {
        "source_code": job["source_code"],
        "language_id": language_id,
        "stdin": case.get("input_text", ""),
        "cpu_time_limit": max(0.1, float(limits["time_ms"]) / 1000),
        "wall_time_limit": max(1.0, float(limits["time_ms"]) / 1000 + 1),
        "memory_limit": int(limits["memory_mb"]) * 1024,
        "max_file_size": 1024,
        "enable_network": False,
        "redirect_stderr_to_stdout": False,
    }
    response = client.post(
        f"{JUDGE0_URL}/submissions",
        params={"base64_encoded": "false", "wait": "true"},
        headers=_judge_headers(),
        json=payload,
    )
    response.raise_for_status()
    result = response.json()
    if "status" not in result and result.get("token"):
        result = _wait_for_result(client, result["token"])
    status_id = int(result.get("status", {}).get("id", 13))
    status = "completed"
    if status_id == 5:
        status = "time_limit"
    elif status_id == 6:
        status = "compile_error"
    elif 7 <= status_id <= 12 or status_id == 14:
        status = "runtime_error"
    elif status_id != 3:
        status = "internal_error"
    stderr = result.get("stderr") or result.get("compile_output") or result.get("message") or ""
    try:
        execution_ms = max(0, int(float(result.get("time") or 0) * 1000))
    except (TypeError, ValueError):
        execution_ms = 0
    try:
        memory_kb = max(0, int(float(result.get("memory") or 0)))
    except (TypeError, ValueError):
        memory_kb = 0
    return {
        "test_case_id": case["id"],
        "status": status,
        "actual_output": str(result.get("stdout") or "")[:100_000],
        "stderr": str(stderr)[:20_000],
        "execution_ms": execution_ms,
        "memory_kb": memory_kb,
    }


def _fail(client: httpx.Client, job: dict[str, Any], error: Exception):
    try:
        response = client.post(
            f"{BACKEND_URL}/internal/coding/jobs/{job['job_id']}/fail",
            headers=_headers(),
            json={
                "lease_token": job["lease_token"],
                "error": f"{type(error).__name__}: {error}"[:2000],
                "retryable": True,
            },
        )
        response.raise_for_status()
    except Exception:
        logger.exception("Could not release failed job %s", job.get("job_id"))


def run():
    if len(RUNNER_TOKEN) < 32:
        raise SystemExit("CODE_RUNNER_TOKEN must contain at least 32 characters")
    from urllib.parse import urlparse
    endpoint = urlparse(JUDGE0_URL)
    if endpoint.scheme not in {"http", "https"} or not endpoint.hostname or endpoint.username or endpoint.password:
        raise SystemExit("JUDGE0_URL must identify a configured private Judge0 HTTP(S) endpoint without embedded credentials")
    with httpx.Client(timeout=httpx.Timeout(35, connect=5)) as client:
        language_ids: dict[str, int] = {}
        refresh_languages_at = 0.0
        while True:
            try:
                if time.monotonic() >= refresh_languages_at:
                    language_ids = _language_ids(client)
                    refresh_languages_at = time.monotonic() + 600
                    logger.info("Judge languages ready: %s", ", ".join(sorted(language_ids)))
                response = client.post(
                    f"{BACKEND_URL}/internal/coding/jobs/claim",
                    headers=_headers(),
                    json={"judge_version": JUDGE_VERSION},
                )
                response.raise_for_status()
                job = response.json().get("job")
                if not job:
                    time.sleep(POLL_SECONDS)
                    continue
                try:
                    results = [
                        _execute_case(client, job, case, language_ids)
                        for case in job["test_cases"]
                    ]
                    completed = client.post(
                        f"{BACKEND_URL}/internal/coding/jobs/{job['job_id']}/complete",
                        headers=_headers(),
                        json={"lease_token": job["lease_token"], "results": results},
                    )
                    completed.raise_for_status()
                    logger.info(
                        "Submission %s completed as %s",
                        job["submission_id"],
                        completed.json().get("status"),
                    )
                except Exception as error:
                    logger.exception("Judge job %s failed", job.get("job_id"))
                    _fail(client, job, error)
            except Exception:
                logger.exception("Code judge control loop failed")
                time.sleep(min(30, POLL_SECONDS * 5))


if __name__ == "__main__":
    run()
