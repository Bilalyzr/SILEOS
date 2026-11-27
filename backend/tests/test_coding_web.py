"""HTML and CSS challenges: definitions, judge payload, and colour-aware checks."""

import json

import pytest

from app.services.web_checks import normalize_css_value, parse_check
from tests.test_coding_analytics import _enrol
from tests.test_coding_assessments import INTERNAL, ROOT, _author, _course


def check(kind, selector, **extra):
    return json.dumps({"kind": kind, "selector": selector, **extra})


def web_definition(languages, *, page_html="", cases=None):
    starter = {"html": page_html} if page_html else {}
    return {
        "title": "Style the heading",
        "problem_statement": "Make the main heading purple and say Welcome.",
        "allowed_languages": languages,
        "starter_code": starter,
        "time_limit_ms": 3000,
        "memory_limit_mb": 128,
        "max_attempts": 10,
        "test_cases": cases
        or [
            {"visibility": "sample", "input_text": check("text", "h1"), "expected_output": "Welcome"},
            {"visibility": "hidden", "input_text": check("css", "h1", property="color"), "expected_output": "#7c3aed"},
        ],
    }


def _publish(client, course, instructor, as_user, definition):
    as_user(instructor)
    _author(client, instructor)
    created = client.post(f"{ROOT}/courses/{course.id}/challenges", json=definition)
    assert created.status_code == 201, created.text
    body = created.json()
    published = client.post(
        f"{ROOT}/challenges/{body['id']}/action",
        json={"action": "publish", "version": body["version"], "reason": "Reviewed"},
    )
    assert published.status_code == 200, published.text
    return published.json()["slug"]


def _claim(client):
    from app.main import app
    from app.routers.coding_judge_internal import require_code_runner

    app.dependency_overrides[require_code_runner] = lambda: None
    claim = client.post(f"{INTERNAL}/jobs/claim", json={"judge_version": "web-1"})
    assert claim.status_code == 200, claim.text
    return claim.json()["job"]


def _complete(client, job, outputs):
    return client.post(
        f"{INTERNAL}/jobs/{job['job_id']}/complete",
        json={
            "lease_token": job["lease_token"],
            "results": [
                {"test_case_id": case["id"], "status": "completed", "actual_output": out}
                for case, out in zip(job["test_cases"], outputs)
            ],
        },
    )


# ---- pure helpers ----------------------------------------------------------

@pytest.mark.parametrize(
    "value, expected",
    [
        ("#7c3aed", "rgb(124, 58, 237)"),
        ("#FFF", "rgb(255, 255, 255)"),
        ("rgb(124,58,237)", "rgb(124, 58, 237)"),
        ("rgba(124, 58, 237, 1)", "rgb(124, 58, 237)"),
        ("rebeccapurple", "rgb(102, 51, 153)"),
        ("1px  solid  RED", "1px solid rgb(255, 0, 0)"),
        ("transparent", "rgba(0, 0, 0, 0)"),
        ("32px", "32px"),
    ],
)
def test_css_values_compare_after_colour_conversion(value, expected):
    assert normalize_css_value(value) == expected


def test_check_parsing_rejects_bad_checks():
    assert parse_check(check("css", "h1", property="Color"))["property"] == "color"
    for bad in ["not json", check("style", "h1"), check("text", ""), check("css", "h1"), check("attr", "a")]:
        with pytest.raises(ValueError):
            parse_check(bad)


# ---- authoring rules -------------------------------------------------------

def test_web_languages_cannot_mix_with_programming_languages(client, db, make_user, as_user):
    instructor, course = _course(db, make_user)
    as_user(instructor)
    _author(client, instructor)
    response = client.post(f"{ROOT}/courses/{course.id}/challenges", json=web_definition(["html", "python"]))
    assert response.status_code == 422
    assert "cannot be mixed" in response.text


def test_css_challenge_needs_page_html_and_valid_checks(client, db, make_user, as_user):
    instructor, course = _course(db, make_user)
    as_user(instructor)
    _author(client, instructor)
    missing_page = client.post(f"{ROOT}/courses/{course.id}/challenges", json=web_definition(["css"]))
    assert missing_page.status_code == 422
    assert "page HTML" in missing_page.text

    bad_check = web_definition(
        ["html"],
        cases=[{"visibility": "hidden", "input_text": "h1 is purple", "expected_output": "yes"}],
    )
    response = client.post(f"{ROOT}/courses/{course.id}/challenges", json=bad_check)
    assert response.status_code == 422
    assert "Test 1" in response.text

    ok = client.post(
        f"{ROOT}/courses/{course.id}/challenges",
        json=web_definition(["css"], page_html="<html><head></head><body><h1>Welcome</h1></body></html>"),
    )
    assert ok.status_code == 201, ok.text
    assert ok.json()["starter_code"]["html"].startswith("<html>")


# ---- judging ---------------------------------------------------------------

def test_css_job_carries_page_html_and_colours_match(client, db, make_user, as_user):
    instructor, course = _course(db, make_user)
    page = "<html><head></head><body><h1>Welcome</h1></body></html>"
    slug = _publish(client, course, instructor, as_user, web_definition(["css"], page_html=page))
    student = make_user(role="student")
    _enrol(db, course, student)
    as_user(student)
    queued = client.post(
        f"{ROOT}/challenges/{slug}/submissions",
        json={"language": "css", "source_code": "h1 { color: #7c3aed; }", "idempotency_key": "web-css-0001"},
    )
    assert queued.status_code == 202, queued.text

    job = _claim(client)
    assert job["language"] == "css"
    assert job["page_html"] == page
    assert json.loads(job["test_cases"][1]["input_text"])["property"] == "color"
    assert all("expected_output" not in case for case in job["test_cases"])

    # The browser reports colours as rgb(); the instructor wrote hex.
    done = _complete(client, job, ["Welcome", "rgb(124, 58, 237)"])
    assert done.status_code == 200, done.text
    assert done.json()["status"] == "passed"


def test_html_job_has_no_page_html_and_wrong_values_fail(client, db, make_user, as_user):
    instructor, course = _course(db, make_user)
    slug = _publish(client, course, instructor, as_user, web_definition(["html"]))
    student = make_user(role="student")
    _enrol(db, course, student)
    as_user(student)
    queued = client.post(
        f"{ROOT}/challenges/{slug}/submissions",
        json={"language": "html", "source_code": "<h1>Hello</h1>", "idempotency_key": "web-html-0001"},
    )
    assert queued.status_code == 202, queued.text
    job = _claim(client)
    assert job["page_html"] == ""
    done = _complete(client, job, ["Hello", "rgb(0, 0, 0)"])
    assert done.status_code == 200, done.text
    assert done.json()["status"] == "failed"
