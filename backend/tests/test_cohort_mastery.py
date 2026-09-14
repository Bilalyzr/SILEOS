"""R10 institution features: class-wise mastery per cohort (SPOC, course
editor, admin) and the college roll-up for school dashboards.
"""
import pytest

from app.models.cohort import Cohort, CohortMembership, College
from app.models.course import Course
from app.models.mastery import LearnerMastery


@pytest.fixture
def instructor(db, make_user):
    from app.models.user import InstructorProfile
    u = make_user(role="instructor", email="cm-inst@example.com")
    db.add(InstructorProfile(user_id=u.id, is_approved=True))
    db.commit()
    return u


@pytest.fixture
def spoc(db, make_user):
    return make_user(role="spoc", email="cm-spoc@example.com")


@pytest.fixture
def setup(db, instructor, spoc, student_user, make_user):
    from app.models.sileos_pack import StudentRiskFlag
    other = make_user(role="student", email="cm-other@example.com")
    course = Course(post_title="Cohort course", post_content="d", post_excerpt="p", post_status="publish", post_author=instructor.id, course_price=0, course_type="seyappaduporul")
    college = College(name="Sasha School", slug="sasha-school", created_by=instructor.id)
    db.add_all([course, college])
    db.commit()
    cohort = Cohort(college_id=college.id, course_id=course.id, spoc_user_id=spoc.id, name="Class 10-A", slug="class-10-a")
    db.add(cohort)
    db.commit()
    db.add_all([CohortMembership(cohort_id=cohort.id, user_id=student_user.id), CohortMembership(cohort_id=cohort.id, user_id=other.id)])
    db.add_all([
        LearnerMastery(user_id=student_user.id, concept="trigonometry", estimate=30.0, confidence=0.6, evidence_count=2),
        LearnerMastery(user_id=student_user.id, concept="algebra", estimate=80.0, confidence=0.6, evidence_count=2),
        LearnerMastery(user_id=other.id, concept="trigonometry", estimate=40.0, confidence=0.6, evidence_count=2),
    ])
    db.add(StudentRiskFlag(course_id=course.id, user_id=student_user.id, risk_score=70, severity="high", reasons=["weak concepts"]))
    db.commit()
    return course, college, cohort, other


def _h(user):
    from app.core.security import create_access_token
    return {"Authorization": f"Bearer {create_access_token({'sub': str(user.id)})}"}


def test_cohort_mastery_access_and_payload(client, db, setup, spoc, instructor, student_user, make_user):
    course, college, cohort, other = setup
    stranger = make_user(role="spoc", email="cm-stranger@example.com")
    assert client.get(f"/api/v1/cohorts/spoc/cohorts/{cohort.id}/mastery", headers=_h(stranger)).status_code == 403
    assert client.get(f"/api/v1/cohorts/spoc/cohorts/{cohort.id}/mastery", headers=_h(student_user)).status_code == 403
    for who in (spoc, instructor):   # the SPOC and the course editor both see it
        r = client.get(f"/api/v1/cohorts/spoc/cohorts/{cohort.id}/mastery", headers=_h(who))
        assert r.status_code == 200, r.text
    d = r.json()
    assert d["members"] == 2 and d["concepts"][0] == {"concept": "trigonometry", "average": 35.0, "learners": 2, "below_50": 2}
    weak = [s for s in d["students"] if s["user_id"] == student_user.id][0]
    assert weak["average"] == 55.0 and weak["weakest"] == "trigonometry" and weak["risk"]["severity"] == "high"
    assert d["students"][0]["user_id"] == other.id   # lowest average first (40 < 55)
    assert d["class_average"] == 47.5


def test_college_rollup_admin_only(client, db, setup, spoc, make_user):
    course, college, cohort, other = setup
    assert client.get(f"/api/v1/cohorts/admin/colleges/{college.id}/mastery", headers=_h(spoc)).status_code == 403
    admin = make_user(role="admin", email="cm-admin@example.com")
    r = client.get(f"/api/v1/cohorts/admin/colleges/{college.id}/mastery", headers=_h(admin))
    assert r.status_code == 200, r.text
    row = r.json()["cohorts"][0]
    assert row["cohort_name"] == "Class 10-A" and row["members"] == 2 and row["at_risk"] == 1 and row["weakest_concept"] == "trigonometry"
