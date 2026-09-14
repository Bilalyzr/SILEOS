from datetime import date, datetime, timedelta, timezone
from types import SimpleNamespace
import io
import importlib.util
from pathlib import Path
import pytest
from PIL import Image
from sqlalchemy import create_engine, inspect
from alembic.migration import MigrationContext
from alembic.operations import Operations
from app.models.institution import Institution, InstitutionMember, InstitutionInvite
from app.models.campus_operations import (
    CampusAttendance,
    CampusScore,
    CampusSubscription,
    CampusMailJob,
)
from app.models.course import Course
from app.services import campus_billing

ROOT = "/api/v1/institutions"


@pytest.fixture
def setup_campus(client, as_user, make_user, db):
    owner = make_user(role="instructor", email="college-owner@example.org")
    as_user(owner)
    iid = client.post(
        ROOT, json={"name": "Test College", "academic_year": "2026"}
    ).json()["id"]
    bid = client.post(
        f"{ROOT}/{iid}/batches", json={"name": "Year One", "academic_year": "2026"}
    ).json()["id"]
    student = make_user()
    other = make_user()
    members = []
    for u in (student, other):
        m = InstitutionMember(
            institution_id=iid,
            user_id=u.id,
            role="student",
            status="active",
            department="",
        )
        db.add(m)
        db.flush()
        members.append(m)
    db.commit()
    client.post(
        f"{ROOT}/{iid}/batches/{bid}/members",
        json={"member_ids": [m.id for m in members]},
    )
    return SimpleNamespace(
        owner=owner, student=student, other=other, iid=iid, bid=bid, members=members
    )


def test_bulk_preview_then_atomic_import(setup_campus, client, db):
    c = setup_campus
    url = f"{ROOT}/{c.iid}/people/import"
    bad = "email,role,department\nfirst@example.org,student,Science\nbad-email,student,Arts"
    preview = client.post(url, json={"csv": bad}).json()
    assert preview["errors"] == 1
    assert client.post(url, json={"csv": bad, "commit": True}).status_code == 422
    assert db.query(InstitutionInvite).count() == 0
    good = "email,role,department\nfirst@example.org,student,Science\nsecond@example.org,teacher,Arts"
    assert client.post(url, json={"csv": good}).json()["ready"] == 2
    assert db.query(InstitutionInvite).count() == 0
    assert client.post(url, json={"csv": good, "commit": True}).json()["created"] == 2
    assert client.post(url, json={"csv": good, "commit": True}).json()["created"] == 0
    assert db.query(InstitutionInvite).count() == 2


def test_import_duplicate_capacity_and_permissions(setup_campus, client, as_user):
    c = setup_campus
    url = f"{ROOT}/{c.iid}/people/import"
    duplicate = "email\nsame@example.org\nsame@example.org"
    assert client.post(url, json={"csv": duplicate}).json()["errors"] == 1
    many = "email\n" + "\n".join(f"student{i}@example.org" for i in range(100))
    assert client.post(url, json={"csv": many, "commit": True}).status_code == 422
    as_user(c.student)
    assert client.post(url, json={"csv": "email\nnew@example.org"}).status_code == 403


def test_academic_lifecycle_and_student_privacy(setup_campus, client, as_user, db):
    c = setup_campus
    root = f"{ROOT}/{c.iid}"
    term = client.post(
        root + "/terms",
        json={"name": "Semester 1", "starts_on": "2026-01-01", "ends_on": "2026-12-31"},
    )
    assert term.status_code == 201
    aid = client.post(
        root + "/assessments",
        json={
            "batch_id": c.bid,
            "title": "Physics examination",
            "max_score": 50,
            "term_id": term.json()["id"],
        },
    ).json()["id"]
    entries = [
        {"member_id": m.id, "score": 40 + i, "feedback": "Good reasoning"}
        for i, m in enumerate(c.members)
    ]
    assert (
        client.put(
            f"{root}/assessments/{aid}/scores", json={"entries": entries}
        ).status_code
        == 200
    )
    assert (
        client.put(
            f"{root}/assessments/{aid}/scores",
            json={"entries": [{"member_id": c.members[0].id, "score": 51}]},
        ).status_code
        == 422
    )
    assert db.query(CampusScore).count() == 2
    attendance = {
        "batch_id": c.bid,
        "day": date.today().isoformat(),
        "entries": [{"member_id": m.id, "status": "present"} for m in c.members],
    }
    assert client.put(root + "/attendance", json=attendance).status_code == 200
    assert client.put(root + "/attendance", json=attendance).status_code == 200
    assert db.query(CampusAttendance).count() == 2
    as_user(c.student)
    output = client.get(root + "/academics", params={"batch_id": c.bid}).json()
    assert [s["id"] for s in output["students"]] == [c.members[0].id]
    assert len(output["assessments"][0]["scores"]) == 1
    assert client.put(root + "/attendance", json=attendance).status_code == 403


def test_invalid_term_and_cross_batch_writes_are_atomic(setup_campus, client, db):
    c = setup_campus
    root = f"{ROOT}/{c.iid}"
    assert (
        client.post(
            root + "/terms",
            json={
                "name": "Bad term",
                "starts_on": "2027-01-01",
                "ends_on": "2026-01-01",
            },
        ).status_code
        == 422
    )
    assert (
        client.post(
            root + "/assessments",
            json={
                "batch_id": c.bid,
                "title": "Quiz",
                "max_score": 100,
                "term_id": 9999,
            },
        ).status_code
        == 404
    )
    data = {
        "batch_id": c.bid,
        "day": date.today().isoformat(),
        "entries": [
            {"member_id": c.members[0].id, "status": "present"},
            {"member_id": 99999, "status": "absent"},
        ],
    }
    assert client.put(root + "/attendance", json=data).status_code == 422
    assert db.query(CampusAttendance).count() == 0


def test_private_resource_access_and_suspension(
    setup_campus, client, as_user, make_user, db
):
    c = setup_campus
    root = f"{ROOT}/{c.iid}"
    r = client.post(
        root + "/resources",
        data={"title": "Lesson notes", "batch_id": str(c.bid)},
        files={"file": ("notes.txt", b"Newton\nSecond law", "text/plain")},
    )
    assert r.status_code == 201, r.text
    resource = r.json()["id"]
    url = f"{root}/resources/{resource}/download"
    as_user(make_user(role="admin"))
    assert client.get(url).status_code == 404
    as_user(c.student)
    response = client.get(url)
    assert response.content == b"Newton\nSecond law"
    assert response.headers["Cache-Control"] == "private, no-store"
    assert "attachment" in response.headers["content-disposition"]
    c.members[0].status = "suspended"
    db.commit()
    assert client.get(url).status_code == 404


def test_resources_reject_active_formats_and_wrong_batches(setup_campus, client):
    root = f"{ROOT}/{setup_campus.iid}"
    assert (
        client.post(
            root + "/resources",
            data={"title": "Unsafe"},
            files={"file": ("x.html", b"<script>alert(1)</script>", "text/html")},
        ).status_code
        == 422
    )
    assert (
        client.post(
            root + "/resources",
            data={"title": "Wrong batch", "batch_id": "99999"},
            files={"file": ("x.txt", b"hello", "text/plain")},
        ).status_code
        == 404
    )


def test_banner_upload_is_reencoded_and_private(
    setup_campus, client, as_user, make_user
):
    root = f"{ROOT}/{setup_campus.iid}"
    out = io.BytesIO()
    Image.new("RGB", (40, 20), "orange").save(out, "JPEG")
    assert (
        client.put(
            root + "/branding/image",
            files={"file": ("banner.jpg", out.getvalue(), "image/jpeg")},
        ).status_code
        == 200
    )
    response = client.get(root + "/branding/image")
    assert response.content.startswith(b"\x89PNG")
    assert client.get(root + "/branding").json()["has_image"]
    as_user(make_user())
    assert client.get(root + "/branding/image").status_code == 404


def test_email_not_configured_never_claims_delivery(
    setup_campus, client, db, monkeypatch
):
    from app.services import campus_mail

    c = setup_campus
    root = f"{ROOT}/{c.iid}"
    invite = client.post(
        root + "/invitations", json={"email": "invited@example.org"}
    ).json()["id"]
    monkeypatch.setattr(campus_mail, "mail_configured", lambda: False)
    assert client.post(f"{root}/invitations/{invite}/send-email").status_code == 503
    assert db.query(CampusMailJob).count() == 0


def test_guardian_requires_student_consent_then_can_be_revoked(
    client, as_user, make_user
):
    parent = make_user(role="parent")
    student = make_user()
    stranger = make_user()
    as_user(parent)
    r = client.post("/api/v1/parents/children", json={"email": student.user_email})
    assert r.json()["status"] == "pending"
    assert client.get("/api/v1/parents/children").json()["children"] == []
    as_user(student)
    request = client.get("/api/v1/parents/access-requests").json()[0]["id"]
    as_user(stranger)
    assert (
        client.patch(
            f"/api/v1/parents/access-requests/{request}", json={"status": "approved"}
        ).status_code
        == 404
    )
    as_user(student)
    assert (
        client.patch(
            f"/api/v1/parents/access-requests/{request}", json={"status": "approved"}
        ).status_code
        == 200
    )
    as_user(parent)
    assert len(client.get("/api/v1/parents/children").json()["children"]) == 1
    as_user(student)
    client.patch(
        f"/api/v1/parents/access-requests/{request}", json={"status": "revoked"}
    )
    as_user(parent)
    assert client.get("/api/v1/parents/children").json()["children"] == []


def test_subscription_no_paid_unlock_on_activation_and_idempotent_charge(
    setup_campus, db
):
    c = setup_campus
    row = CampusSubscription(
        institution_id=c.iid,
        plan="campus",
        gateway_plan_id="plan_test",
        gateway_subscription_id="sub_test",
        status="created",
    )
    db.add(row)
    db.commit()
    end = int((datetime.now(timezone.utc) + timedelta(days=30)).timestamp())
    payload = {
        "created_at": 100,
        "payload": {
            "subscription": {
                "entity": {"id": "sub_test", "plan_id": "plan_test", "current_end": end}
            },
            "payment": {"entity": {"id": "pay_test", "status": "captured"}},
        },
    }
    event = SimpleNamespace(event_type="subscription.activated", payload=payload)
    assert campus_billing.handle_event(db, event)
    assert campus_billing.effective_plan(db, c.iid) == "starter"
    event.event_type = "subscription.charged"
    campus_billing.handle_event(db, event)
    campus_billing.handle_event(db, event)
    assert campus_billing.effective_plan(db, c.iid) == "campus"
    event.event_type = "subscription.cancelled"
    event.payload["created_at"] = 110
    campus_billing.handle_event(db, event)
    assert row.status == "cancelled"
    assert campus_billing.effective_plan(db, c.iid) == "campus"
    event.event_type = "subscription.activated"
    event.payload["created_at"] = 90
    campus_billing.handle_event(db, event)
    assert row.status == "cancelled"
    row.paid_through = datetime.now(timezone.utc) - timedelta(seconds=1)
    db.flush()
    assert campus_billing.effective_plan(db, c.iid) == "starter"


def test_subscription_disabled_without_prices_and_scoped(
    setup_campus, client, as_user, make_user, monkeypatch
):
    c = setup_campus
    monkeypatch.setattr(campus_billing, "configured_plans", lambda: {})
    assert (
        client.post(
            f"{ROOT}/{c.iid}/billing/subscribe", json={"plan": "campus"}
        ).status_code
        == 503
    )
    as_user(make_user(role="admin"))
    assert client.get(f"{ROOT}/{c.iid}/billing").status_code == 404


def test_public_share_does_not_publish_drafts(client, db, make_user):
    author = make_user(role="instructor")
    course = Course(
        post_author=author.id,
        post_title="<Unsafe title>",
        post_name="banner-course",
        post_status="draft",
    )
    db.add(course)
    db.commit()
    assert client.get(f"/api/v1/share/courses/{course.id}").status_code == 404
    course.post_status = "publish"
    db.commit()
    html = client.get(f"/api/v1/share/courses/{course.id}")
    assert html.status_code == 200
    assert "&lt;Unsafe title&gt;" in html.text and "<Unsafe title>" not in html.text
    png = client.get(f"/api/v1/share/courses/{course.id}/image.png")
    assert png.content.startswith(b"\x89PNG")
    assert Image.open(io.BytesIO(png.content)).size == (1200, 630)


def test_campus_migration_round_trip():
    path = Path(__file__).parents[1] / "alembic/versions/0031_campus_operations.py"
    spec = importlib.util.spec_from_file_location("campus_migration", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    engine = create_engine("sqlite://")
    with engine.begin() as connection:
        module.op = Operations(MigrationContext.configure(connection))
        module.upgrade()
        assert len(inspect(connection).get_table_names()) == 9
        module.downgrade()
        assert inspect(connection).get_table_names() == []
        module.upgrade()
        assert "campus_subscriptions" in inspect(connection).get_table_names()


def test_checkout_pins_reviewed_price_and_blocks_uncertain_retry(
    setup_campus, client, db, monkeypatch
):
    c = setup_campus
    monkeypatch.setattr(
        campus_billing, "configured_plans", lambda: {"campus": "plan_current"}
    )
    calls = []

    def create(body):
        calls.append(body)
        raise TimeoutError()

    monkeypatch.setattr(
        campus_billing,
        "provider",
        lambda: SimpleNamespace(subscription=SimpleNamespace(create=create)),
    )
    url = f"{ROOT}/{c.iid}/billing/subscribe"
    assert (
        client.post(
            url, json={"plan": "campus", "expected_plan_id": "plan_old"}
        ).status_code
        == 409
    )
    assert calls == []
    assert (
        client.post(
            url, json={"plan": "campus", "expected_plan_id": "plan_current"}
        ).status_code
        == 502
    )
    assert (
        client.post(
            url, json={"plan": "campus", "expected_plan_id": "plan_current"}
        ).status_code
        == 409
    )
    assert len(calls) == 1 and db.query(CampusSubscription).count() == 1


def test_signed_charge_recovers_checkout_timeout(setup_campus, db):
    c = setup_campus
    row = CampusSubscription(
        institution_id=c.iid,
        plan="campus",
        gateway_plan_id="plan_current",
        status="creating",
    )
    db.add(row)
    db.commit()
    payload = {
        "created_at": 123,
        "payload": {
            "subscription": {
                "entity": {
                    "id": "sub_recovered",
                    "plan_id": "plan_current",
                    "notes": {
                        "institution_id": str(c.iid),
                        "campus_attempt": str(row.id),
                    },
                    "current_end": int(
                        (datetime.now(timezone.utc) + timedelta(days=30)).timestamp()
                    ),
                }
            },
            "payment": {"entity": {"id": "pay_recovered", "status": "captured"}},
        },
    }
    campus_billing.handle_event(
        db, SimpleNamespace(payload=payload, event_type="subscription.charged")
    )
    assert row.gateway_subscription_id == "sub_recovered" and row.status == "active"
    assert campus_billing.effective_plan(db, c.iid) == "campus"


def test_recovery_cannot_adopt_another_campus_subscription(
    setup_campus, db, client, as_user, make_user, monkeypatch
):
    c = setup_campus
    row = CampusSubscription(
        institution_id=c.iid,
        plan="campus",
        gateway_plan_id="plan_current",
        status="creating",
    )
    db.add(row)
    db.commit()
    entity = {
        "id": "sub_other",
        "plan_id": "plan_current",
        "status": "active",
        "notes": {"institution_id": "9999", "campus_attempt": str(row.id)},
    }
    monkeypatch.setattr(
        campus_billing,
        "provider",
        lambda: SimpleNamespace(subscription=SimpleNamespace(fetch=lambda _: entity)),
    )
    url = f"{ROOT}/platform/billing-attempts/{row.id}/reconcile"
    assert client.post(url, json={"subscription_id": "sub_other"}).status_code == 403
    as_user(make_user(role="admin"))
    assert client.post(url, json={"subscription_id": "sub_other"}).status_code == 409
    db.refresh(row)
    assert row.gateway_subscription_id is None


def test_email_job_records_provider_success_and_does_not_resend(
    setup_campus, client, db, monkeypatch
):
    from contextlib import contextmanager
    from app.services import campus_mail

    c = setup_campus
    url = f"{ROOT}/{c.iid}"
    invite = client.post(
        url + "/invitations", json={"email": "delivery@example.org"}
    ).json()["id"]

    @contextmanager
    def session():
        yield db

    monkeypatch.setattr(campus_mail, "SessionLocal", session)
    monkeypatch.setattr(campus_mail, "mail_configured", lambda: True)
    calls = []

    def send(*args):
        calls.append(args)
        return True

    monkeypatch.setattr(campus_mail.EmailService, "_send_smtp_email", send)
    assert client.post(f"{url}/invitations/{invite}/send-email").status_code == 202
    assert db.query(CampusMailJob).one().status == "sent"
    assert (
        client.post(f"{url}/invitations/{invite}/send-email").json()["status"] == "sent"
    )
    assert len(calls) == 1

def test_private_campus_course_lifecycle_and_no_public_leak(setup_campus,client,db,as_user,make_user):
    from app.models.campus_operations import CampusLessonProgress
    from app.models.enrollment import Enrollment
    c=setup_campus;root=f'{ROOT}/{c.iid}/learning-courses'
    created=client.post(root,json={'title':'Private physics','summary':'For this class only','batch_id':c.bid})
    assert created.status_code==201
    cid=created.json()['id'];url=f'{root}/{cid}'
    assert client.put(url+'/publish',json={'published':True}).status_code==422
    lid=client.post(url+'/lessons',json={'title':'First principles','body':'A private classroom lesson.'}).json()['id']
    as_user(c.student);assert client.get(root).json()==[]
    assert client.get(url).status_code==404
    as_user(c.owner);assert client.put(url+'/publish',json={'published':True}).status_code==200
    as_user(make_user(role='admin'));assert client.get(url).status_code==404
    as_user(c.student);assert client.get(url).json()['content'][0]['body']=='A private classroom lesson.'
    for _ in range(2):assert client.put(f'{url}/lessons/{lid}/complete').status_code==200
    assert db.query(CampusLessonProgress).count()==1
    assert db.query(Enrollment).count()==0
    assert db.query(Course).filter_by(post_title='Private physics').count()==0
    assert client.get(url+'/progress').status_code==403
    assert client.put(url+'/publish',json={'published':False}).status_code==403
    as_user(c.owner);assert client.get(url+'/progress').json()[0]['completed']==1
    client.put(url+'/publish',json={'published':False})
    as_user(c.student);assert client.get(url).status_code==404
    assert db.query(CampusLessonProgress).count()==1

def test_private_course_rejects_wrong_batch_and_resource_audience(setup_campus,client,db,make_user,as_user):
    c=setup_campus;root=f'{ROOT}/{c.iid}'
    cid=client.post(root+'/learning-courses',json={'title':'Everyone course'}).json()['id']
    resource=client.post(root+'/resources',data={'title':'Class-only worksheet','batch_id':str(c.bid)},files={'file':('x.txt',b'private','text/plain')}).json()['id']
    assert client.post(f'{root}/learning-courses/{cid}/lessons',json={'title':'Leak attempt','body':'Cannot share batch-only resource to all members','resource_id':resource}).status_code==422
    private=client.post(root+'/learning-courses',json={'title':'Class-only course','batch_id':c.bid}).json()['id']
    assert client.post(f'{root}/learning-courses/{private}/lessons',json={'title':'Worksheet','body':'Read the attachment','resource_id':resource}).status_code==201
    assert client.delete(f'{root}/resources/{resource}').status_code==409
    client.put(f'{root}/learning-courses/{private}/publish',json={'published':True})
    outsider=make_user();db.add(InstitutionMember(institution_id=c.iid,user_id=outsider.id,role='student',status='active',department=''));db.commit();as_user(outsider)
    assert client.get(f'{root}/learning-courses/{private}').status_code==404

def test_private_learning_migration_round_trip():
    path=Path(__file__).parents[1]/'alembic/versions/0032_campus_learning.py'
    spec=importlib.util.spec_from_file_location('learning_migration',path);module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    engine=create_engine('sqlite://')
    with engine.begin() as connection:
        module.op=Operations(MigrationContext.configure(connection))
        module.upgrade();assert len(inspect(connection).get_table_names())==3
        module.downgrade();assert inspect(connection).get_table_names()==[]
