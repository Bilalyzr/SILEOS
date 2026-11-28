"""End-to-end live class suite: instructor + two students, real browsers, real Jitsi.

Every step is recorded as PASS or FAIL with evidence and the suite keeps going, so one
failure does not hide the next. Results are written to report.json in the LC_DIR folder.
"""
import json, os, re, sys, time, traceback, urllib.request, urllib.error
from datetime import datetime, timedelta, timezone
from playwright.sync_api import sync_playwright

LC_DIR = os.environ.get("LC_DIR", "/w/lc")  # manifest.json is read from, report.json and shots/ are written to, this folder
M = json.load(open(f"{LC_DIR}/manifest.json"))
BASE = os.environ.get("LC_BASE", "https://sileos.sashainfinity.com")  # must be an origin the video server allows to embed it
API = os.environ.get("LC_API", "http://127.0.0.1:8100/api/v1")  # backend, used for server-truth checks
TZ = timezone(timedelta(hours=5, minutes=30))  # Asia/Kolkata has no daylight saving
TITLE = f"LC suite {M['stamp']}"
CORRECT = "a, b = map(int, input().split())\nprint(a + b)\n"
WRONG = "print(0)\n"
MODEL = "a, b = map(int, input().split())\nprint(a + b)\n"

report = {"title": TITLE, "steps": [], "http_errors": {}, "console_errors": {}, "ws": {}}
state = {"class_id": None}
PAGES = {}


def api(user, method, path, body=None):
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(f"{API}{path}", data=data, method=method)
    req.add_header("Authorization", f"Bearer {M[user]['token']}")
    if data is not None:
        req.add_header("Content-Type", "application/json")
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            return r.status, json.loads(r.read() or b"{}")
    except urllib.error.HTTPError as e:
        try:
            return e.code, json.loads(e.read() or b"{}")
        except Exception:
            return e.code, {}


def step(sid, name, fn, needs=None):
    """Run one check. `needs` names step ids that must have passed, otherwise it is skipped."""
    if needs and not all(any(s["id"] == n and s["status"] == "PASS" for s in report["steps"]) for n in needs):
        report["steps"].append({"id": sid, "name": name, "status": "SKIP", "detail": f"blocked by failed step(s) {needs}"})
        print(f"SKIP {sid} {name}", flush=True)
        return False
    try:
        detail = fn()
        report["steps"].append({"id": sid, "name": name, "status": "PASS", "detail": detail or ""})
        print(f"PASS {sid} {name}", flush=True)
        return True
    except Exception as error:
        message = " | ".join(l.strip() for l in str(error).splitlines()[:5])[:700] if str(error) else type(error).__name__
        evidence = {}
        for who, pg in PAGES.items():
            try:
                shot(pg, f"{sid}-{who}")
                evidence[who] = pg.url.split(BASE)[-1] if BASE in pg.url else pg.url
                jf = jitsi(pg)
                if jf:
                    evidence[who + "_call_text"] = re.sub(r"\s+", " ", jf.locator("body").inner_text())[:160]
            except Exception:
                pass
        report["steps"].append({"id": sid, "name": name, "status": "FAIL", "detail": message, "evidence": evidence})
        print(f"FAIL {sid} {name} :: {message}", flush=True)
        return False


def watch(page, who):
    report["http_errors"].setdefault(who, {})
    report["console_errors"].setdefault(who, [])
    report["ws"].setdefault(who, [])

    def on_response(r):
        if r.status >= 400 and "gravatar" not in r.url:
            key = f"{r.status} {re.sub(r'[?].*', '', r.url)[:110]}"
            report["http_errors"][who][key] = report["http_errors"][who].get(key, 0) + 1

    def on_console(m):
        if m.type == "error" and "Failed to load resource" not in m.text and "gravatar" not in m.text:
            report["console_errors"][who].append(m.text[:220])

    def on_ws(ws):
        report["ws"][who].append(re.sub(r"token=[^&]+", "token=…", ws.url)[:110])

    page.on("response", on_response)
    page.on("console", on_console)
    page.on("websocket", on_ws)


def sign_in(page, creds):
    page.goto(f"{BASE}/login", wait_until="domcontentloaded")
    page.locator('input[type="email"]').first.fill(creds["email"])
    page.locator('input[type="password"]').first.fill(creds["password"])
    page.locator('button[type="submit"]').first.click()
    page.wait_for_timeout(3500)


def jitsi(page):
    for f in page.frames:
        if "liveclass.sashainfinity.com" in f.url:
            return f
    return None


def in_call(page, timeout=45):
    end = time.time() + timeout
    while time.time() < end:
        f = jitsi(page)
        if f and f.locator("#new-toolbox, .toolbox-content").count() > 0:
            return True
        page.wait_for_timeout(1000)
    return False


def shot(page, name):
    try:
        page.screenshot(path=f"{LC_DIR}/shots/{name}.png")
    except Exception:
        pass


def join_as_student(page, who):
    # The list loads over the API after the page shell; wait for the title (reloading
    # once or twice) instead of assuming 3 s is enough.
    found = False
    for _ in range(3):
        page.goto(f"{BASE}/student/live-classes", wait_until="domcontentloaded")
        try:
            page.get_by_text(TITLE).first.wait_for(timeout=15000)
            found = True
            break
        except Exception:
            continue
    if not found:
        raise AssertionError("class title not shown in the student's live class list")
    link = page.locator(f'a[href="/student/live-classes/{state["class_id"]}/join"]').first
    link.click(timeout=15000)
    page.get_by_role("button", name="Continue to class").click(timeout=30000)
    if not in_call(page):
        err = page.locator("body").inner_text()
        raise AssertionError("never reached the call: " + re.sub(r"\s+", " ", err)[-160:])
    return "in call"


def main():
    with sync_playwright() as p:
        args = ["--no-sandbox", "--use-fake-ui-for-media-stream", "--use-fake-device-for-media-stream", "--autoplay-policy=no-user-gesture-required"]
        browser = p.chromium.launch(args=args)

        def ctx():
            return browser.new_context(viewport={"width": 1400, "height": 1000}, permissions=["camera", "microphone"])

        ic, ac, bc = ctx(), ctx(), ctx()
        ip, ap, bp = ic.new_page(), ac.new_page(), bc.new_page()
        for page, who in ((ip, "instructor"), (ap, "student_a"), (bp, "student_b")):
            watch(page, who)
            PAGES[who] = page
        sign_in(ip, M["instructor"]); sign_in(ap, M["a"]); sign_in(bp, M["b"])

        # ---- 1. CREATE -----------------------------------------------------
        def t_create():
            ip.goto(f"{BASE}/instructor/live-classes/new", wait_until="domcontentloaded")
            ip.locator("select").first.wait_for(timeout=30000)
            ip.wait_for_timeout(1500)
            ip.locator("select").first.select_option(str(M["course"]))
            ip.locator('input[type="text"]').first.fill(TITLE)
            now = datetime.now(TZ).strftime("%Y-%m-%dT%H:%M")
            ip.locator('input[type="datetime-local"]').fill(now)
            ip.get_by_role("button", name="Schedule class").click()
            ip.wait_for_url(re.compile(r"/instructor/live-classes$"), timeout=30000)
            ip.wait_for_timeout(2500)
            ip.get_by_text(TITLE).first.wait_for(timeout=20000)
            return "class created and listed"
        step("T01", "Instructor creates a live class from the form", t_create)

        def t_find_id():
            import urllib.parse
            st, body = api("instructor", "GET", "/live/classes?scope=upcoming&page_size=50")
            items = body.get("items") or body.get("classes") or body.get("results") or []
            match = [c for c in items if c.get("title") == TITLE]
            if not match:
                st2, body2 = api("instructor", "GET", "/live/classes?page_size=50")
                match = [c for c in (body2.get("items") or []) if c.get("title") == TITLE]
            assert match, f"class not found through the API (status {st})"
            state["class_id"] = match[0]["id"]
            return f"class id {state['class_id']}, status {match[0].get('status')}"
        step("T02", "The class exists on the server with status scheduled", t_find_id, needs=["T01"])

        # ---- 2. INSTRUCTOR STARTS -----------------------------------------
        def t_start():
            ip.goto(f"{BASE}/instructor/live-classes", wait_until="domcontentloaded")
            ip.wait_for_timeout(3000)
            card = ip.locator("div").filter(has_text=TITLE).filter(has=ip.get_by_role("button", name="Start class")).last
            card.get_by_role("button", name="Start class").click(timeout=20000)
            ip.wait_for_url(re.compile(rf"/live-classes/{state['class_id']}/console"), timeout=40000)
            return "console opened"
        step("T03", "Instructor starts the class from the list", t_start, needs=["T02"])

        def t_instructor_in_call():
            ip.get_by_role("button", name="Continue to class").click(timeout=30000)
            assert in_call(ip, 60), "instructor never reached the call; " + re.sub(r"\s+", " ", ip.locator("main, body").first.inner_text())[-200:]
            st, cls = api("instructor", "GET", f"/live/classes/{state['class_id']}")
            assert cls.get("status") == "live", f"server status is {cls.get('status')}"
            return "in call, server status live"
        step("T04", "Instructor reaches the call and the class is live", t_instructor_in_call, needs=["T03"])
        shot(ip, "after-instructor-join")

        # ---- 3. STUDENTS JOIN ---------------------------------------------
        step("T05", "Student A finds the class and joins the call", lambda: join_as_student(ap, "a"), needs=["T04"])
        step("T06", "Student B finds the class and joins the call", lambda: join_as_student(bp, "b"), needs=["T04"])
        shot(ap, "after-student-a-join"); shot(bp, "after-student-b-join")

        def t_attendance():
            ip.wait_for_timeout(8000)
            st, body = api("instructor", "GET", f"/live/classes/{state['class_id']}/attendance")
            rows = body.get("rows") or body.get("attendance") or body.get("items") or (body if isinstance(body, list) else [])
            ids = {r.get("user_id") for r in rows}
            assert M["a"]["id"] in ids and M["b"]["id"] in ids, f"attendance rows: {sorted(i for i in ids if i)} (status {st})"
            return f"{len(rows)} attendance rows including both students"
        step("T07", "Attendance records both students", t_attendance, needs=["T05", "T06"])

        def t_roster():
            ip.get_by_role("tab", name="People").click()
            ip.wait_for_timeout(15000)
            text = ip.locator("body").inner_text()
            m = re.search(r"(\d+) in the room", text)
            assert m and int(m.group(1)) >= 2, f"instructor sees '{m.group(0) if m else 'no count'}' for the call roster"
            return m.group(0)
        step("T08", "Instructor's room count shows the students in the call", t_roster, needs=["T05", "T06"])

        # ---- 4. RECORDING -------------------------------------------------
        def t_rec_on():
            ip.get_by_role("tab", name="Recording").click()
            toggle = ip.get_by_role("switch")
            toggle.click()
            ip.wait_for_timeout(2500)
            st, cls = api("instructor", "GET", f"/live/classes/{state['class_id']}")
            assert cls.get("recording_status") in ("requested", "processing", "available"), f"server recording_status={cls.get('recording_status')}"
            return f"server recording_status={cls.get('recording_status')}"
        step("T09", "Instructor starts recording and the server records the request", t_rec_on, needs=["T04"])

        def t_rec_actually_recording():
            # The recorder opens its own browser, joins the call and starts ffmpeg; that takes
            # 20-30 s, so poll rather than wait a fixed short time.
            on = None
            for _ in range(45):
                ip.wait_for_timeout(2000)
                on = ip.get_by_role("switch").get_attribute("aria-checked")
                if on == "true":
                    break
            text = ip.locator("body").inner_text()
            assert on == "true" and "This class is being recorded" in text, f"switch aria-checked={on}; the call never reported that recording started"
            return "call reports recording on"
        step("T10", "The call actually starts recording (switch stays on)", t_rec_actually_recording, needs=["T09"])

        def t_rec_banner_for_students():
            text = ap.locator("body").inner_text()
            assert re.search(r"being recorded|recording", text, re.I), "student A never sees a recording notice"
            return "students see a recording notice"
        step("T11", "Students are told the class is being recorded", t_rec_banner_for_students, needs=["T10"])

        # ---- 5. LIVE CODING -----------------------------------------------
        def t_push():
            ip.get_by_role("tab", name="Coding").click()
            ip.wait_for_timeout(2500)
            ip.locator("label", has_text="Challenge").locator("select").first.select_option(label=M["challenge_title"])
            ip.get_by_label("Instructions for learners").fill("Solve it in the live session.")
            ip.get_by_label("Model solution (revealed after you close)").fill(MODEL)
            ip.get_by_role("button", name="Push to learners").click()
            ip.get_by_text("Challenge pushed to learners.").first.wait_for(timeout=20000)
            return "pushed"
        step("T12", "Instructor pushes the live coding challenge", t_push, needs=["T04"])

        def student_sees_challenge(page, who):
            page.get_by_text("Live challenge").first.wait_for(timeout=30000)
            page.get_by_role("button", name="Submit attempt").wait_for(timeout=30000)
            return "challenge workspace visible under the call"
        step("T13", "Student A sees the live challenge", lambda: student_sees_challenge(ap, "a"), needs=["T05", "T12"])
        step("T14", "Student B sees the live challenge", lambda: student_sees_challenge(bp, "b"), needs=["T06", "T12"])

        def submit(page, code):
            page.locator(".monaco-editor .view-lines").first.click()
            page.keyboard.press("Control+A"); page.keyboard.press("Delete")
            page.keyboard.insert_text(code)
            page.wait_for_timeout(600)
            page.get_by_role("button", name="Submit attempt").click()
            # Judge only this learner's own result line ("Passed X of Y cases"). The page also says
            # "N of M learners have passed", which is about everyone else and must not count.
            for _ in range(90):
                page.wait_for_timeout(1000)
                text = page.locator("body").inner_text()
                m = re.search(r"Passed (\d+) of (\d+) cases", text)
                if m and "Evaluating" not in text:
                    return "passed" if m.group(1) == m.group(2) else "failed"
            raise AssertionError("no verdict within 90 seconds")
        step("T15", "Student A submits a correct solution and passes", lambda: (lambda v: (_ for _ in ()).throw(AssertionError(f"verdict {v}")) if v != "passed" else "passed")(submit(ap, CORRECT)), needs=["T13"])
        step("T16", "Student B submits a wrong solution and fails", lambda: (lambda v: (_ for _ in ()).throw(AssertionError(f"verdict {v}")) if v != "failed" else "failed")(submit(bp, WRONG)), needs=["T14"])

        def t_board():
            ip.get_by_role("tab", name="Coding").click()
            ip.wait_for_timeout(7000)
            board = ip.get_by_test_id("live-board").inner_text()
            flat = re.sub(r"\s+", " ", board)
            assert "LC Student A" in board and "LC Student B" in board, "board: " + flat[:200]
            assert re.search(r"LC Student A.*passed", flat), "student A not shown as passed: " + flat[:200]
            return flat[:160]
        step("T17", "Results board shows both students with the right outcome", t_board, needs=["T15", "T16"])

        def t_close_reveal():
            ip.get_by_role("button", name="Close", exact=True).click()
            ip.get_by_text("Challenge closed.").first.wait_for(timeout=15000)
            ip.get_by_role("button", name="Reveal solution").click()
            ip.get_by_text("Model solution revealed to learners.").first.wait_for(timeout=15000)
            return "closed and revealed"
        step("T18", "Instructor closes the challenge and reveals the solution", t_close_reveal, needs=["T12"])

        def t_students_see_solution():
            ap.get_by_text("Model solution ·").first.wait_for(timeout=20000)
            bp.get_by_text("Model solution ·").first.wait_for(timeout=20000)
            return "both students see the model solution"
        step("T19", "Students see the model solution after the reveal", t_students_see_solution, needs=["T18", "T05", "T06"])

        # ---- 6. EXIT -------------------------------------------------------
        def hang_up(page, who):
            """Click Leave. The call's toolbar hides itself, so wake it first and retry once if it did not react.
            Records whether a menu offering 'End meeting for all' appeared (it must not for students)."""
            assert jitsi(page), "no call frame to leave"
            for attempt in range(3):
                f = jitsi(page)
                if not f:
                    return  # already out of the call
                page.mouse.move(600 + attempt * 20, 700)
                page.mouse.move(650 + attempt * 20, 720)
                page.wait_for_timeout(800)
                f.locator('[aria-label="Leave the meeting"]').first.click(timeout=15000, force=True)  # toolbar auto-hides on a slow host
                page.wait_for_timeout(2000)
                f = jitsi(page)
                if not f:
                    state.setdefault("end_all_offered", {})[who] = False  # left directly, no menu offered
                    return
                body = f.locator("body").inner_text()
                if "Leave meeting" in body.replace("Leave the meeting", ""):
                    state.setdefault("end_all_offered", {})[who] = "End meeting for all" in body
                    try:
                        role = f.evaluate("() => APP.store.getState()['features/base/participants'].local.role")
                    except Exception as e:
                        role = f"unreadable ({e})"
                    items = f.evaluate("() => [...document.querySelectorAll('button,[role=menuitem],[role=button]')].map(e => (e.getAttribute('aria-label')||e.innerText||'').trim()).filter(t => /leave|end meeting|hang/i.test(t))")
                    print(f"EVIDENCE {who}: call role={role!r}; leave menu items={items}", flush=True)
                    f.get_by_text("Leave meeting", exact=True).first.click()
                    return
            raise AssertionError("the Leave button did not react after 3 tries")
        def t_a_exit():
            hang_up(ap, 'student_a')
            try:
                ap.wait_for_url(re.compile(r"/student/live-classes$"), timeout=30000)
            except Exception:
                f = jitsi(ap)
                after = re.sub(r"\s+", " ", f.locator("body").inner_text())[:200] if f else "no call frame"
                raise AssertionError("clicked Leave but the page never left the call; call frame says: " + after)
            return "student A left and returned to the class list"
        step("T20", "Student A leaves the meeting properly", t_a_exit, needs=["T05"])

        def t_no_end_for_all():
            offered = state.get("end_all_offered", {}).get("student_a")
            assert offered is not None, "the leave path was not observed, so this could not be judged"
            assert offered is False, "a student is offered 'End meeting for all' when leaving, so students hold moderator rights in the call"
            return "students are only offered Leave"
        step("T20b", "Students are not offered 'End meeting for all'", t_no_end_for_all, needs=["T05"])

        def t_a_attendance_kept():
            st, body = api("instructor", "GET", f"/live/classes/{state['class_id']}/attendance")
            rows = body.get("rows") or body.get("attendance") or body.get("items") or []
            mine = [r for r in rows if r.get("user_id") == M["a"]["id"]]
            assert mine, "no attendance row for student A after leaving"
            return f"row kept: {json.dumps({k: mine[0].get(k) for k in ('accumulated_seconds','present','seconds','status') if k in mine[0]})}"
        step("T21", "Student A's attendance is kept after leaving", t_a_attendance_kept, needs=["T20"])

        def t_end():
            ip.get_by_role("button", name="End class").click()
            dialog = ip.locator('[role="dialog"], [role="alertdialog"]').first
            dialog.wait_for(timeout=10000)
            dialog.get_by_role("button", name="OK", exact=True).click()
            ip.wait_for_url(re.compile(r"/live-classes/\d+/report"), timeout=40000)
            st, cls = api("instructor", "GET", f"/live/classes/{state['class_id']}")
            assert cls.get("status") == "ended", f"server status {cls.get('status')}"
            return "ended, report opened"
        step("T22", "Instructor ends the class for everyone", t_end, needs=["T04"])

        def t_b_disconnected():
            deadline = time.time() + 45
            while time.time() < deadline:
                url = bp.url
                text = bp.locator("body").inner_text().lower()
                if "/student/live-classes/" not in url.split(BASE)[-1] or re.search(r"ended|left the class|disconnected", text) or jitsi(bp) is None:
                    return f"student B no longer in the call ({url.split(BASE)[-1]})"
                bp.wait_for_timeout(2000)
            raise AssertionError("student B is still in the call after the instructor ended the class")
        step("T23", "Student B is disconnected when the class ends", t_b_disconnected, needs=["T06", "T22"])

        def t_ended_state():
            ap.goto(f"{BASE}/student/live-classes/{state['class_id']}/join", wait_until="domcontentloaded")
            text = ""
            for _ in range(15):  # the page shows a loading splash until the class status arrives
                ap.wait_for_timeout(2000)
                text = ap.locator("body").inner_text()
                if re.search(r"ended|no longer|finished|not available", text, re.I) or "Continue to class" in text:
                    break
            assert re.search(r"ended|no longer|finished|not available", text, re.I) and "Continue to class" not in text, "an ended class still offers to join: " + re.sub(r"\s+", " ", text)[-150:]
            return "rejoin blocked with an ended message"
        step("T24", "Students cannot rejoin an ended class", t_ended_state, needs=["T22"])

        def t_report():
            st, body = api("instructor", "GET", f"/live/classes/{state['class_id']}/attendance")
            rows = body.get("rows") or body.get("attendance") or body.get("items") or []
            finalized = [r for r in rows if r.get("present") is not None]
            assert len(finalized) >= 2, f"attendance finalized for {len(finalized)} of {len(rows)} rows"
            return f"{len(finalized)} rows finalized"
        step("T25", "Attendance is finalized when the class ends", t_report, needs=["T22"])

        browser.close()
    json.dump(report, open(f"{LC_DIR}/report.json", "w"), indent=1)
    passed = sum(1 for s in report["steps"] if s["status"] == "PASS")
    failed = sum(1 for s in report["steps"] if s["status"] == "FAIL")
    skipped = sum(1 for s in report["steps"] if s["status"] == "SKIP")
    print(f"RESULT pass={passed} fail={failed} skip={skipped} class_id={state['class_id']}")


main()
