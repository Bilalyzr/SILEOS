from datetime import datetime, timedelta, timezone

from app.models.campus_pilot import CampusAnnouncement, CampusEvent
from app.models.institution import InstitutionBatch, InstitutionBatchMember, InstitutionMember


ROOT = "/api/v1/institutions"


def setup_workspace(client, db, as_user, make_user):
    owner = make_user(role="instructor")
    learner = make_user(role="student")
    as_user(owner)
    institution_id = client.post(
        ROOT,
        json={"name": "Today School", "kind": "school", "academic_year": "2026-27"},
    ).json()["id"]
    member = InstitutionMember(
        institution_id=institution_id,
        user_id=learner.id,
        role="student",
        status="active",
        department="Grade 6",
    )
    batch = InstitutionBatch(
        institution_id=institution_id,
        name="Grade 6 A",
        department="Grade 6",
        academic_year="2026-27",
    )
    db.add_all([member, batch])
    db.flush()
    db.add(InstitutionBatchMember(batch_id=batch.id, member_id=member.id))
    now = datetime.now(timezone.utc)
    db.add_all(
        [
            CampusEvent(
                institution_id=institution_id,
                batch_id=batch.id,
                title="Mathematics",
                kind="class",
                room="Room 4",
                description="Fractions",
                starts_at=now,
                ends_at=now + timedelta(hours=1),
                series="test-series",
                created_by=owner.id,
            ),
            CampusAnnouncement(
                institution_id=institution_id,
                batch_id=batch.id,
                title="Science fair",
                body="Bring your project plan on Friday.",
                created_by=owner.id,
            ),
        ]
    )
    db.commit()
    return owner, learner, institution_id, member


def test_today_is_role_aware_and_task_status_is_mutable(
    client, db, as_user, make_user
):
    owner, learner, institution_id, member = setup_workspace(
        client, db, as_user, make_user
    )
    root = f"{ROOT}/{institution_id}"
    as_user(owner)
    task = client.post(
        root + "/today/actions",
        json={
            "title": "Call the guardian",
            "detail": "Discuss the new support plan.",
            "priority": "high",
            "assigned_member_id": member.id,
        },
    )
    assert task.status_code == 201, task.text
    task_id = task.json()["id"]

    staff_today = client.get(root + "/today")
    assert staff_today.status_code == 200, staff_today.text
    assert staff_today.json()["role"] == "owner"
    assert any(item["id"] == task_id for item in staff_today.json()["actions"])

    as_user(learner)
    learner_today = client.get(root + "/today")
    assert learner_today.status_code == 200
    body = learner_today.json()
    assert body["role"] == "student"
    assert body["schedule"][0]["title"] == "Mathematics"
    assert body["notices"][0]["title"] == "Science fair"
    assert any(item["id"] == task_id for item in body["actions"])
    done = client.patch(root + f"/today/actions/{task_id}", json={"status": "done"})
    assert done.status_code == 200
    assert done.json()["status"] == "done"
    assert not any(
        item["id"] == task_id for item in client.get(root + "/today").json()["actions"]
    )


def test_today_hides_other_institutions(client, db, as_user, make_user):
    owner, _learner, institution_id, _member = setup_workspace(
        client, db, as_user, make_user
    )
    outsider = make_user(role="instructor")
    as_user(outsider)
    assert client.get(f"{ROOT}/{institution_id}/today").status_code == 404
    assert (
        client.post(
            f"{ROOT}/{institution_id}/today/actions", json={"title": "No access"}
        ).status_code
        == 404
    )

