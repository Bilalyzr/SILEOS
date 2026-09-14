"""Read-only HTTP acceptance, bounded load, and isolated SQLite restore evidence.

Never touches live providers or mutates the target app. Example:
python scripts/validate_saas_release.py --url http://127.0.0.1:8014 --requests 120 --concurrency 8
"""
import argparse
from concurrent.futures import ThreadPoolExecutor
import json
from pathlib import Path
import sqlite3
import statistics
import time
import urllib.request
import urllib.error
from urllib.parse import urlsplit

ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--url", default="http://127.0.0.1:8014")
    parser.add_argument("--requests", type=int, default=120)
    parser.add_argument("--concurrency", type=int, default=8)
    parser.add_argument("--p95-ms", type=float, default=1500)
    parser.add_argument("--allow-remote", action="store_true")
    args = parser.parse_args()
    parsed = urlsplit(args.url)
    if parsed.scheme not in ("http", "https") or parsed.username or parsed.password:
        parser.error("Use an HTTP(S) base URL without embedded credentials")
    if parsed.hostname not in ("127.0.0.1", "localhost", "::1") and not args.allow_remote:
        parser.error("Remote load requires an explicit --allow-remote")
    if not 1 <= args.requests <= 10000 or not 1 <= args.concurrency <= 64:
        parser.error("Use 1..10000 requests and 1..64 concurrent clients")
    routes = ["/health", "/api/v1/virtual-labs", "/api/v1/lab-studio/curriculum", "/api/v1/courses/"]
    def get(index):
        path = routes[index % len(routes)]
        started = time.perf_counter()
        try:
            with urllib.request.urlopen(args.url.rstrip("/") + path, timeout=15) as response:
                body = response.read()
                status = response.status
                if "application/json" in response.headers.get("Content-Type", ""):
                    json.loads(body)
            return {"path": path, "status": status, "ms": round((time.perf_counter() - started) * 1000, 2)}
        except Exception as exc:
            return {"path": path, "status": getattr(exc, "code", 0), "error": type(exc).__name__}
    started = time.perf_counter()
    with ThreadPoolExecutor(max_workers=args.concurrency) as pool:
        samples = list(pool.map(get, range(args.requests)))
    duration = time.perf_counter() - started
    latency = sorted(s["ms"] for s in samples if s.get("status") == 200)
    p95 = latency[min(len(latency) - 1, int(len(latency) * .95))] if latency else None
    report = {"target": args.url, "requests": args.requests, "concurrency": args.concurrency,
        "duration_seconds": round(duration, 2), "throughput_rps": round(args.requests / duration, 2),
        "p50_ms": statistics.median(latency) if latency else None, "p95_ms": p95,
        "failed_requests": [s for s in samples if s.get("status") != 200],
        "capacity_certified": False, "scope": "Local public read journeys only; provider and target-sized load acceptance remain separate."}
    demo = ROOT / ".local/saas-demo/campus-preview.sqlite"
    if demo.is_file():
        restored = ROOT / ".local/saas-demo/restore-validation.sqlite"
        # backup API gives a consistent snapshot; only the disposable restore is written.
        with sqlite3.connect(demo.as_uri() + "?mode=ro", uri=True) as source, sqlite3.connect(restored) as target:
            source.backup(target)
            assert target.execute("PRAGMA integrity_check").fetchone()[0] == "ok"
            tables = [r[0] for r in source.execute("SELECT name FROM sqlite_master WHERE type='table'")]
            for name in tables:
                safe = '"' + name.replace('"', '""') + '"'
                assert source.execute("SELECT COUNT(*) FROM " + safe).fetchone() == target.execute("SELECT COUNT(*) FROM " + safe).fetchone()
            report["restore"] = {"status": "passed", "tables_compared": len(tables), "engine": "sqlite", "production_restore": False}
    report["passed"] = not report["failed_requests"] and p95 is not None and p95 <= args.p95_ms
    out = ROOT / ".local/saas-release-validation.json"
    out.parent.mkdir(exist_ok=True)
    out.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps(report, indent=2))
    raise SystemExit(0 if report["passed"] else 1)


if __name__ == "__main__":
    main()
