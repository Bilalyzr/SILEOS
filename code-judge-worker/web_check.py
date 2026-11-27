"""HTML and CSS judging: render the learner's page in headless Chromium and read check values.

Safety: page JavaScript is disabled, the context is offline, and every request
the page tries to make (images, fonts, stylesheets, iframes) is aborted, so a
submission cannot reach the network or the internal services. The checks run
through Playwright's evaluation channel, which still works with page scripts off.
"""

from __future__ import annotations

import json
import logging
import time
from typing import Any


logger = logging.getLogger("code-judge-worker.web")

# Reads one value from the rendered page. Raises on an invalid selector.
PROBE_JS = """([kind, selector, extra]) => {
  const nodes = document.querySelectorAll(selector);
  if (kind === 'count') return String(nodes.length);
  if (kind === 'exists') return nodes.length ? 'true' : 'false';
  const el = nodes[0];
  if (!el) return '';
  if (kind === 'text') return (el.textContent || '').trim().replace(/\\s+/g, ' ');
  if (kind === 'attr') return el.getAttribute(extra) ?? '';
  if (kind === 'css') return getComputedStyle(el).getPropertyValue(extra).trim();
  throw new Error('Unknown check kind');
}"""


def build_document(language: str, source: str, page_html: str) -> str:
    """The page to render: the learner's HTML, or the instructor's page with the learner's CSS."""
    if language == "html":
        return source
    # Keep the learner's CSS inside its <style> element.
    css = source.replace("</style", "<\\/style")
    style = f"<style>\n{css}\n</style>"
    lowered = page_html.lower()
    index = lowered.find("</head>")
    if index != -1:
        return page_html[:index] + style + page_html[index:]
    return style + page_html


class WebJudge:
    """One Chromium for the worker's lifetime; a fresh, isolated context per submission."""

    def __init__(self) -> None:
        self._playwright = None
        self._browser = None

    def _ensure_browser(self):
        if self._browser is None or not self._browser.is_connected():
            from playwright.sync_api import sync_playwright

            if self._playwright is None:
                self._playwright = sync_playwright().start()
            self._browser = self._playwright.chromium.launch(args=["--disable-gpu", "--disable-dev-shm-usage"])
        return self._browser

    def run(self, job: dict[str, Any]) -> list[dict[str, Any]]:
        browser = self._ensure_browser()
        document = build_document(job["language"], job["source_code"], job.get("page_html", ""))
        timeout_ms = max(1000, min(int(job["limits"]["time_ms"]), 10000))
        context = browser.new_context(
            java_script_enabled=False,
            offline=True,
            viewport={"width": 1280, "height": 800},
        )
        try:
            context.route("**/*", lambda route: route.abort())
            page = context.new_page()
            page.set_default_timeout(timeout_ms)
            started = time.monotonic()
            page.set_content(document, wait_until="domcontentloaded", timeout=timeout_ms)
            render_ms = int((time.monotonic() - started) * 1000)
            return [self._check(page, case, render_ms) for case in job["test_cases"]]
        finally:
            context.close()

    @staticmethod
    def _check(page, case: dict[str, Any], render_ms: int) -> dict[str, Any]:
        started = time.monotonic()
        try:
            check = json.loads(case["input_text"])
            extra = check.get("property") or check.get("attribute") or ""
            value = page.evaluate(PROBE_JS, [check["kind"], check["selector"], extra])
            status, output, stderr = "completed", str(value), ""
        except Exception as error:
            message = str(error).splitlines()[0] if str(error) else type(error).__name__
            status, output, stderr = "runtime_error", "", message[:500]
        return {
            "test_case_id": case["id"],
            "status": status,
            "actual_output": output[:100_000],
            "stderr": stderr,
            "execution_ms": render_ms + int((time.monotonic() - started) * 1000),
            "memory_kb": 0,
        }

    def close(self) -> None:
        try:
            if self._browser is not None:
                self._browser.close()
            if self._playwright is not None:
                self._playwright.stop()
        except Exception:
            logger.exception("Could not close the web judge browser")
