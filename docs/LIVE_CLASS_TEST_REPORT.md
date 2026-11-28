# Live class workflow: end-to-end test report

Date: 2026-11-27. Environment: dev (`https://sileos.sashainfinity.com`), real video server, one
instructor and two students in three separate browsers.
Suite: [`e2e/live-class/`](../e2e/live-class/README.md).

## Result of the final run

**26 of 26 steps passed.** The workflow now works end to end through the public site: create and start a class,
two students join, the call is recorded (a real video file is produced and students see the banner), the
instructor pushes a live coding test, students submit (one passes, one fails), the results board and model
solution work, a student leaves, students are not moderators, the instructor ends the class, the other student is
disconnected, rejoin is blocked and attendance is finalized.

## Failures, causes and status

| ID | What failed | Functionality affected | Root cause | Status |
|---|---|---|---|---|
| LC-01 | A class created for "now", or started late, vanished from every list | Scheduling, starting a late class, students joining it | The Upcoming list required `scheduled_start >= now`. A scheduled class past its start time was not Upcoming, not Live (not started) and not Past (end not reached) | **Fixed**: Upcoming now uses the scheduled end. 2 regression tests |
| LC-02 | Two token tests failed | Test suite only | Tests expected `"true"` strings; the code deliberately sends booleans (string values silently granted no moderator rights) | **Fixed**: tests assert booleans |
| LC-03 | Call never appeared, page stayed on "Connecting" | Joining any class from `sileos.sashainfinity.com` | The video server only allowed `sashainfinity.com`, `www.` and `lms.` to embed it (`frame-ancestors`) | **Fixed**: added `sileos.` and `dev.` in the live class vhost |
| LC-04 | "WebSocket connection could not be established", HTTP 502 | Joining any class | `jitsi-web` proxied to `xmpp.meet.jitsi`, a name the stack never defined (the chat server is `prosody`) | **Fixed**: `meet.conf` points at `prosody` |
| LC-05 | "Couldn't connect to the class: Invalid signature" | Joining from dev | Dev signed call tokens with its own key; the video server accepts only its own | **Fixed**: dev uses the video server's key (owner's decision) |
| LC-06 | Same "WebSocket connection" error for real browsers | Joining, especially from shared networks | The shared per-IP limit (10 r/s, burst 20) rejected the call's WebSocket during the page's burst of requests | **Fixed**: WebSocket and static assets exempt on the live class host; page keeps a limit |
| LC-07 | Students stayed in the call after the instructor ended the class (T23) | Ending a class | The end only changed the database. A student's call logged the server's "ended" answer and did nothing | **Fixed**: students' calls check the class every 10 s and leave; the instructor's End class also closes the video room. 5 tests |
| LC-08 | An ended class still offered the device check and Join (T24) | Rejoining / old links | The join page never read the class status | **Fixed**: shows "This class has ended" (or cancelled), with the recording link when there is one. 5 tests |
| LC-09 | Dock tabs clipped; panel shifted sideways | Instructor controls at normal window widths | Five tabs in a narrow panel with `overflow-hidden` | **Fixed**: the tab row scrolls by itself |
| LC-10 | Server said "recording requested" while the call said "Recording unavailable" | Recording status, class end, reports | The request is stored before the call tries; nothing corrected it on failure, and class end would then wait for a file that never comes | **Fixed**: new `POST /live/classes/{id}/recording/failed`, called when the call reports an error; the dock shows why. 6 tests |
| LC-11 | **Recording cannot start** (T10, T11) | Session recording, the student recording notice, playback and transcripts | Four causes in a row: (1) the recorder was in a Docker profile that was never started; (2) the host had no `snd_aloop` module and the stack mapped no `/dev/snd`; (3) prosody created the recorder's login domain from `XMPP_HIDDEN_DOMAIN` (default `hidden.meet.jitsi`) while the recorder and web config use `recorder.meet.jitsi`, so the recorder could not log in (`no-auth-mech`); (4) the recorder needs ~15-25 s to start its browser, just over Jicofo's 15 s reply timeout, so Jicofo cancelled starts that were working | **Fixed**: recorder started with a persistent `snd_aloop`, `/dev/snd` and `DISPLAY` mapped, health check path corrected, `XMPP_HIDDEN_DOMAIN=recorder.meet.jitsi`, Jicofo reply timeout 60 s. A real MP4 is recorded |
| LC-12 | **Students are moderators** (T20b) | Classroom control: a student is offered "End meeting for all" and moderator tools | Two causes: prosody lacked `token_affiliation`, and Jicofo's JWT authentication promotes every logged-in user to moderator regardless of the token claim (a student's call role was `moderator`) | **Fixed**: `XMPP_MUC_MODULES=token_affiliation`, plus `deploy/jitsi/jicofo/custom-jicofo.conf` with `authentication.enabled=false` and `enable-auto-owner=false`. Moderators now come only from the signed token |
| LC-13 | **Code is blocked by the firewall** (T12, T15, T16) | Live coding push, student code submissions, HTML/CSS challenges | The host firewall (Coraza, OWASP CRS 4.25) rule 932370 "Windows command injection" matches `print` at the start of a line; ordinary Python and JavaScript got 403 | **Fixed (owner approved)**: detection-only mode for the coding endpoints (path-traversal and `;`/`//` tricks still blocked). Applied to the running firewall container and restarted; see the drift warning below |

Test mistakes found along the way (not product defects): wrong selectors for a labelled dropdown, the End class
confirmation button (labelled "OK"), the Leave menu, and a verdict check that read "1 of 1 learners have
passed" as the learner's own result. The suite now reads the learner's own "Passed X of Y cases" line.

## Things to know (not defects, but must not be forgotten)

- **Firewall drift.** The LC-13 rule was applied to the running firewall container's `/etc/caddy/Caddyfile`. The source
  file `/opt/incubaseos/waf/Caddyfile` belongs to another project and was not edited, so if that project rebuilds the
  firewall image, the rule is lost and code submissions return 403 again. The rule text is in the knowledge base.
- **Recording uploads.** Recordings are picked up by the recording worker, which may upload to the video CDN and call a
  transcription service. The test recordings were deleted from the recorder afterwards.
- **Recorder start time.** Recording takes 15-30 s to begin; the instructor's switch turns on only then.

## Other observations (not changed)

- The call logs "getting turn credentials failed: is mod_turncredentials installed and configured?". No TURN relay
  is set up, so people on restrictive networks may not get audio or video.
- The LMS site's own per-IP limit still answers 429 to API calls and scripts when several people share one IP
  (seen with three test browsers). A classroom behind one network address could hit it.
- Every student page load logs `404 /api/v1/memberships/me`. It does not break anything visible.

## Tests added

Backend: 2 (class listing), 3 (recording failure report); 2 token tests corrected. Frontend: 8 for the call
ending, 5 for the ended-class page, 3 for the recording error. End to end: `e2e/live-class/` (25 steps plus a
live-coding-only run that avoids the firewall).
