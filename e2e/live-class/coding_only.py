"""Live coding steps without the firewall: same UI, dev address (localhost:4100) instead of the public domain.
The call itself cannot load from this origin (Jitsi only allows the public hosts), but the live coding
panel and the dock are independent of the call, so the coding logic can be checked on its own."""
import json, os, re, time
from playwright.sync_api import sync_playwright

LC_DIR = os.environ.get("LC_DIR", "/w/lc")
M = json.load(open(f"{LC_DIR}/manifest.json"))
BASE = os.environ.get("LC_LOCAL_BASE", "http://localhost:4100")  # dev address that does not pass through the firewall
CLASS_ID = int(os.environ["LC_LIVE_CLASS_ID"])  # a class that is already live and owned by the instructor
CORRECT = "a, b = map(int, input().split())\nprint(a + b)\n"
WRONG = "print(0)\n"
results = []
def check(cid, name, fn):
    try:
        detail = fn()
        results.append((cid, name, "PASS", detail or "")); print(f"PASS {cid} {name}", flush=True)
        return True
    except Exception as e:
        msg = " | ".join(l.strip() for l in str(e).splitlines()[:4])[:420]
        results.append((cid, name, "FAIL", msg)); print(f"FAIL {cid} {name} :: {msg}", flush=True)
        return False

def sign_in(page, c):
    page.goto(f"{BASE}/login", wait_until="domcontentloaded")
    page.locator('input[type="email"]').first.fill(c["email"]); page.locator('input[type="password"]').first.fill(c["password"])
    page.locator('button[type="submit"]').first.click(); page.wait_for_timeout(3500)

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

with sync_playwright() as p:
    b = p.chromium.launch(args=["--no-sandbox", "--use-fake-ui-for-media-stream", "--use-fake-device-for-media-stream"])
    mk = lambda: b.new_context(viewport={"width": 1400, "height": 1000}, permissions=["camera", "microphone"]).new_page()
    ip, ap, bp = mk(), mk(), mk()
    sign_in(ip, M["instructor"]); sign_in(ap, M["a"]); sign_in(bp, M["b"])
    ip.goto(f"{BASE}/instructor/live-classes/{CLASS_ID}/console", wait_until="domcontentloaded")
    ip.get_by_role("button", name="Continue to class").click(timeout=30000); ip.wait_for_timeout(6000)
    for pg in (ap, bp):
        pg.goto(f"{BASE}/student/live-classes/{CLASS_ID}/join", wait_until="domcontentloaded")
        pg.get_by_role("button", name="Continue to class").click(timeout=30000); pg.wait_for_timeout(5000)

    def push():
        ip.get_by_role("tab", name="Coding").click(); ip.wait_for_timeout(2000)
        ip.locator("label", has_text="Challenge").locator("select").first.select_option(label=M["challenge_title"])
        ip.get_by_label("Instructions for learners").fill("Solve it in the live session.")
        ip.get_by_label("Model solution (revealed after you close)").fill(CORRECT)
        ip.get_by_role("button", name="Push to learners").click()
        ip.get_by_text("Challenge pushed to learners.").first.wait_for(timeout=20000)
    check("C1", "Instructor pushes the live coding challenge", push)
    def sees(pg):
        pg.get_by_text("Live challenge").first.wait_for(timeout=30000)
        pg.get_by_role("button", name="Submit attempt").wait_for(timeout=30000)
    check("C2", "Student A sees the live challenge", lambda: sees(ap))
    check("C3", "Student B sees the live challenge", lambda: sees(bp))
    check("C4", "Student A submits a correct solution and passes", lambda: (lambda v: None if v == "passed" else (_ for _ in ()).throw(AssertionError(f"verdict {v}")))(submit(ap, CORRECT)))
    check("C5", "Student B submits a wrong solution and fails", lambda: (lambda v: None if v == "failed" else (_ for _ in ()).throw(AssertionError(f"verdict {v}")))(submit(bp, WRONG)))
    def board():
        ip.get_by_role("tab", name="Coding").click(); ip.wait_for_timeout(7000)
        flat = re.sub(r"\s+", " ", ip.get_by_test_id("live-board").inner_text())
        assert "LC Student A" in flat and "LC Student B" in flat, "board: " + flat[:200]
        assert re.search(r"LC Student A.*passed", flat), flat[:200]
        return flat[:150]
    check("C6", "Results board shows both students with the right outcome", board)
    def close_reveal():
        ip.get_by_role("button", name="Close", exact=True).click(); ip.get_by_text("Challenge closed.").first.wait_for(timeout=15000)
        ip.get_by_role("button", name="Reveal solution").click(); ip.get_by_text("Model solution revealed to learners.").first.wait_for(timeout=15000)
    check("C7", "Instructor closes the challenge and reveals the solution", close_reveal)
    def solution():
        ap.get_by_text("Model solution ·").first.wait_for(timeout=20000); bp.get_by_text("Model solution ·").first.wait_for(timeout=20000)
    check("C8", "Students see the model solution after the reveal", solution)
    def late_submit_blocked():
        # the challenge is closed: a late submit must be refused by the server, not silently accepted
        import urllib.request, urllib.error
        live_id = None
        req = urllib.request.Request(f"http://127.0.0.1:8100/api/v1/live/classes/{CLASS_ID}/coding-challenges", headers={"Authorization": "Bearer " + M["a"]["token"]})
        items = json.load(urllib.request.urlopen(req))
        live_id = items[0]["id"]
        req = urllib.request.Request(f"http://127.0.0.1:8100/api/v1/live/coding-challenges/{live_id}/submissions", method="POST",
            data=json.dumps({"language": "python", "source_code": CORRECT, "idempotency_key": "late-submit-0001"}).encode(),
            headers={"Authorization": "Bearer " + M["a"]["token"], "Content-Type": "application/json"})
        try:
            urllib.request.urlopen(req); raise AssertionError("a submission after the challenge closed was accepted")
        except urllib.error.HTTPError as e:
            assert e.code == 409, f"expected 409, got {e.code}"
        return "409 after close"
    check("C9", "A submission after the challenge is closed is refused", late_submit_blocked)
    b.close()
json.dump(results, open(f"{LC_DIR}/coding_only.json", "w"), indent=1)
print("RESULT", sum(1 for r in results if r[2] == "PASS"), "passed,", sum(1 for r in results if r[2] == "FAIL"), "failed")
