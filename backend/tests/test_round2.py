"""Round 2 (items 4, 5, 9): instructor earnings + PDF report, banks at
scale (push random draw into a quiz, CSV export, per-attempt subset), and
the media pipeline (tool status, tier build 503 without gltf-transform,
tiered streaming, audio rendition hook).
"""
import io
from datetime import datetime, timedelta, timezone

import pytest

from app.models.course import Course
from app.models.enrollment import Enrollment
from app.models.quiz import Quiz, QuizAttempt, QuizQuestion


@pytest.fixture
def instructor(db, make_user):
    from app.models.user import InstructorProfile
    u = make_user(role="instructor", email="r2-inst@example.com")
    db.add(InstructorProfile(user_id=u.id, is_approved=True))
    db.commit()
    return u


@pytest.fixture
def headers(client, instructor, auth_headers):
    return auth_headers(instructor.user_email)


@pytest.fixture
def student_headers(student_user):
    from app.core.security import create_access_token
    return {"Authorization": f"Bearer {create_access_token({'sub': str(student_user.id)})}"}


@pytest.fixture
def course(db, instructor, student_user):
    c = Course(post_title="Round two course", post_content="d", post_excerpt="p", post_status="publish", post_author=instructor.id,
               course_price=499, course_type="utporul")
    db.add(c)
    db.commit()
    db.refresh(c)
    db.add(Enrollment(user_id=student_user.id, course_id=c.id, enrollment_status="enrolled"))
    db.commit()
    return c


# ---------------------------------------------------------------- item 4

def test_earnings_and_pdf(client, db, course, instructor, student_user, headers, student_headers):
    from app.models.payment import Order, OrderItem, OrderStatus, Payment, PaymentStatus
    o = Order(user_id=student_user.id, order_key="ok-1", order_status=OrderStatus.COMPLETED, currency="INR", total_amount=499, subtotal_amount=499)
    db.add(o)
    db.commit()
    db.add(OrderItem(order_id=o.id, course_id=course.id, order_item_name="Round two course", order_item_type="course", quantity=1, subtotal=499, total=499))
    db.add(Payment(order_id=o.id, user_id=student_user.id, payment_method="razorpay", amount=499, currency="INR",
                   payment_status=PaymentStatus.REFUNDED, refund_status="processed"))
    db.commit()
    assert client.get("/api/v1/funnel/instructor/earnings", headers=student_headers).status_code == 403
    r = client.get("/api/v1/funnel/instructor/earnings", headers=headers)
    assert r.status_code == 200, r.text
    row = r.json()["courses"][0]
    assert row["orders"] == 1 and row["gross"] == 499.0 and row["refunds"] == 499.0 and row["net"] == 0.0 and row["refund_rate"] == 100.0
    assert r.json()["totals"]["gross"] == 499.0
    pdf = client.get("/api/v1/funnel/instructor/report.pdf?days=30", headers=headers)
    assert pdf.status_code == 200 and pdf.headers["content-type"].startswith("application/pdf") and pdf.content[:4] == b"%PDF"


# ---------------------------------------------------------------- item 5

@pytest.fixture
def bank(db, instructor):
    from app.models.sileos_pack import BankQuestion, QuestionBank
    b = QuestionBank(instructor_id=instructor.id, title="Physics bank")
    db.add(b)
    db.commit()
    for i in range(12):
        db.add(BankQuestion(bank_id=b.id, question_title=f"Bank Q{i}?", question_type="multiple_choice", question_mark=1,
                            options=["a", "b", "c", "d"], correct_answer=i % 4, difficulty=["easy", "medium", "hard"][i % 3], tags=[]))
    db.add(BankQuestion(bank_id=b.id, question_title="Draft?", question_type="multiple_choice", options=["a", "b"], correct_answer=0, tags=["ai-draft"]))
    db.commit()
    return b


def test_push_to_quiz_and_per_attempt_subset(client, db, course, instructor, bank, headers, student_headers):
    q = Quiz(post_author=instructor.id, post_title="Drawn quiz", post_parent=course.id, post_status="publish")
    db.add(q)
    db.commit()
    r = client.post(f"/api/v1/question-banks/{bank.id}/push-to-quiz/{q.id}", headers=headers, json={"count": 8, "difficulty_mix": {"easy": 2, "hard": 2}})
    assert r.status_code == 201, r.text
    assert r.json()["added"] == 8 and r.json()["pool"] == 12 and r.json()["by_difficulty"]["easy"] >= 2 and r.json()["by_difficulty"]["hard"] >= 2
    assert db.query(QuizQuestion).filter(QuizQuestion.quiz_id == q.id).count() == 8
    titles = {x.question_title for x in db.query(QuizQuestion).filter(QuizQuestion.quiz_id == q.id).all()}
    assert "Draft?" not in titles   # ai-draft rows never leave the review queue
    # 3 questions per attempt
    r = client.put(f"/api/v1/courses/{course.id}/quizzes/{q.id}", headers=headers, json={"maxQuestionsForTake": 3})
    assert r.status_code == 200
    assert client.get(f"/api/v1/courses/{course.id}/quizzes/{q.id}", headers=headers).json()["maxQuestionsForTake"] == 3
    start = client.post(f"/api/v1/quizzes/{q.id}/start", headers=student_headers).json()
    assert start["total_questions"] == 3 and len(start["question_ids"]) == 3
    a = db.query(QuizAttempt).filter(QuizAttempt.attempt_id == start["attempt_id"]).one()
    assert a.attempt_info["_question_ids"] == start["question_ids"]
    # resuming returns the same subset
    again = client.post(f"/api/v1/quizzes/{q.id}/start", headers=student_headers).json()
    assert again["resumed"] is True and again["question_ids"] == start["question_ids"]
    # grading only counts the drawn subset: answer all three correctly -> 100%
    answers = {}
    for qid in start["question_ids"]:
        from app.models.quiz import QuizQuestionAnswer
        correct = db.query(QuizQuestionAnswer).filter(QuizQuestionAnswer.belongs_question_id == qid, QuizQuestionAnswer.is_correct.is_(True)).first()
        answers[str(qid)] = correct.answer_title
    r = client.post(f"/api/v1/courses/{course.id}/quizzes/{q.id}/submit", headers=student_headers, json={"answers": answers})
    assert r.status_code == 200, r.text
    assert r.json()["total_marks"] == 3


def test_bank_csv_export_roundtrips(client, db, bank, headers, course):
    r = client.get(f"/api/v1/question-banks/{bank.id}/export.csv", headers=headers)
    assert r.status_code == 200 and r.headers["content-type"].startswith("text/csv")
    lines = r.text.strip().splitlines()
    assert lines[0].startswith("question,type,option_a") and len(lines) == 14
    # the export imports back through the CSV importer (ai-draft row has too few options? it has a,b -> valid)
    r = client.post(f"/api/v1/course-ops/courses/{course.id}/quizzes/import-csv", headers=headers,
                    files={"file": ("bank.csv", r.content, "text/csv")}, data={"title": "Re-imported"})
    assert r.status_code == 201, r.text
    assert r.json()["questions"] == 13


# ---------------------------------------------------------------- item 9

def test_media_tools_tiers_and_audio(client, db, instructor, headers, tmp_path, monkeypatch):
    from app.models.three_d import ThreeDModel
    from app.routers import three_d as three_d_router
    from app.services import media_pipeline as mp
    st = client.get("/api/v1/three-d/tools", headers=headers).json()
    assert set(st) == {"ffmpeg", "gltf_transform"}
    glb = tmp_path / "m.glb"
    glb.write_bytes(b"glTF" + b"\x02\x00\x00\x00" + b"\x00" * 60)
    (tmp_path / "m.t3.glb").write_bytes(b"glTF" + b"\x02\x00\x00\x00" + b"\x00" * 8)
    monkeypatch.setattr(three_d_router, "_resolve", lambda rel: str(tmp_path / rel.split("/")[-1]))
    m = ThreeDModel(owner_id=instructor.id, title="m", file_path="x/m.glb", file_size_bytes=68, format="glb")
    db.add(m)
    db.commit()
    # no tool -> honest 503
    monkeypatch.setattr(mp, "gltf_transform_path", lambda: None)
    r = client.post(f"/api/v1/three-d/models/{m.id}/build-tiers", headers=headers)
    assert r.status_code == 503 and "gltf-transform" in r.json()["detail"]
    # fake tool -> tiers recorded and streamed by ?tier=
    monkeypatch.setattr(mp, "gltf_transform_path", lambda: "fake")
    monkeypatch.setattr(mp, "build_glb_tiers", lambda src, out_dir=None, tiers=("T2", "T3"): {"T3": str(tmp_path / "m.t3.glb")})
    r = client.post(f"/api/v1/three-d/models/{m.id}/build-tiers", headers=headers)
    assert r.status_code == 200, r.text
    assert r.json()["tiers"]["T3"].endswith("m.t3.glb") and r.json()["sizes"]["T3"] == 16
    full = client.get(f"/api/v1/three-d/models/{m.id}/file", headers=headers)
    low = client.get(f"/api/v1/three-d/models/{m.id}/file?tier=T3", headers=headers)
    assert len(full.content) == 68 and len(low.content) == 16 and low.headers["x-tier"] == "T3"
    unknown = client.get(f"/api/v1/three-d/models/{m.id}/file?tier=T2", headers=headers)
    assert len(unknown.content) == 68   # missing tier falls back to the original
    # audio rendition helper points at the sibling and is honest without ffmpeg
    monkeypatch.setattr(mp, "ffmpeg_path", lambda: None)
    with pytest.raises(RuntimeError):
        mp.build_audio_rendition(str(tmp_path / "v.mp4"))
    assert mp.audio_sibling(str(tmp_path / "v.mp4")) is None
    (tmp_path / "v.m4a").write_bytes(b"x")
    assert mp.audio_sibling(str(tmp_path / "v.mp4")).endswith("v.m4a")
