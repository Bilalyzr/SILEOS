# Live class end-to-end suite

Drives a real instructor and two real students in three separate browsers through the whole live class
workflow on the dev site, using the real video server. Every step is recorded as PASS, FAIL or SKIP with
evidence (screenshots of all three browsers at each failure, the HTTP errors each user saw, the call's own
text), and the run keeps going after a failure so one problem does not hide the next.

| Step | Checks |
|---|---|
| T01–T04 | Instructor creates a class from the form, it exists on the server, the instructor starts it and reaches the call |
| T05–T08 | Both students find the class, join, are recorded in attendance, and appear in the instructor's room count |
| T09–T11 | Recording: the server records the request, the call really starts recording, students are told |
| T12–T19 | Live coding: push, both students see it, one passes and one fails, results board, close, reveal solution |
| T20–T25 | Exit: a student leaves, attendance is kept, the instructor ends the class, the other student is disconnected, rejoin is blocked, attendance is finalized |
| T20b | A student must not be offered "End meeting for all" (students must not be moderators) |

`coding_only.py` repeats the live coding steps through the dev address that does not pass through the
host firewall, to tell application problems apart from firewall problems.

## Running it

The suite must run from an origin the video server allows to embed it (`frame-ancestors` in
`/etc/nginx/sites-enabled/sashainfinity-liveclass.conf`), so it uses `https://sileos.sashainfinity.com`.

```bash
# 1. Create two throwaway students and a manifest with tokens (inside the backend container)
docker exec -i -e LC_INSTRUCTOR_EMAIL=<instructor email> -e LC_INSTRUCTOR_PASSWORD=<password> \
  development-backend-1 sh -c 'cd /app && python -' < e2e/live-class/setup.py
docker cp development-backend-1:/tmp/lc_manifest.json /some/work/dir/manifest.json && chmod 600 /some/work/dir/manifest.json

# 2. Run the suite in the Playwright image (needs network access to the site)
docker run --rm --network host -v /some/work/dir:/w/lc -v "$PWD/e2e/live-class:/w/suite:ro" \
  -e LC_DIR=/w/lc mcr.microsoft.com/playwright/python:v1.48.0-jammy \
  sh -c 'pip install -q playwright==1.48.0 && python /w/suite/suite.py'

# 3. Clean up
docker exec -i development-backend-1 sh -c 'cd /app && python -' < e2e/live-class/cleanup_classes.py
docker exec -i development-backend-1 sh -c 'cd /app && python -' < e2e/live-class/cleanup_students.py
```

The test accounts' tokens last three hours. The manifest holds credentials, so keep it out of git.
Results: `report.json` and `shots/` in the work directory.
