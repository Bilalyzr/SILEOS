"""Demo content for the assessment/gamification walkthrough. Throwaway.

Creates on course 1 (Full-Stack Web Development Bootcamp):
- a quiz (2 MC + 1 essay) via DB models,
- a published assignment with a rubric + late policy via DB models,
then drives the REAL student API (login as arjun) to:
- take + submit the quiz (essay answer → pending_review for the grading queue),
- submit a text assignment (→ ungraded submission for the queue),
so gradebook, grading queue, and XP all show live data.
Idempotent-ish: skips creation when titles already exist.
"""
import os

os.environ.setdefault("DATABASE_URL", "sqlite:///./visual_qa.db")
os.environ.setdefault("REDIS_URL", "redis://127.0.0.1:6379/0?socket_connect_timeout=0.05")
os.environ.setdefault("SECRET_KEY", "x" * 64)
os.environ.setdefault("JWT_SECRET", "y" * 64)
os.environ.setdefault("VIDEO_SECRET", "visual-qa-secret-0123456789abcdef")
os.environ.setdefault("ENVIRONMENT", "development")

import requests

from app.core.database import SessionLocal
from app.models.assignment import Assignment
from app.models.quiz import Quiz, QuizQuestion, QuizQuestionAnswer
from app.models.user import User

BASE = "http://127.0.0.1:8000/api/v1"
db = SessionLocal()

instructor = db.query(User).filter(User.user_email == "priya@sashademo.com").first()
COURSE_ID = 1

quiz = db.query(Quiz).filter(Quiz.post_title == "Module 1 Checkpoint Quiz").first()
if not quiz:
    quiz = Quiz(
        post_author=instructor.id,
        post_parent=COURSE_ID,
        post_title="Module 1 Checkpoint Quiz",
        quiz_passing_grade=60,
        quiz_max_attempts_allowed=3,
        quiz_time_limit=30,
    )
    db.add(quiz)
    db.flush()
    q1 = QuizQuestion(quiz_id=quiz.id, question_title="Which hook manages state in React?",
                      question_type="multiple_choice", question_mark=10, question_order=1)
    q2 = QuizQuestion(quiz_id=quiz.id, question_title="HTTP 404 means the resource was found.",
                      question_type="true_false", question_mark=10, question_order=2)
    q3 = QuizQuestion(quiz_id=quiz.id, question_title="Explain the difference between REST and GraphQL in your own words.",
                      question_type="essay", question_mark=20, question_order=3)
    db.add_all([q1, q2, q3])
    db.flush()
    db.add_all([
        QuizQuestionAnswer(belongs_question_id=q1.question_id, answer_title="useState", is_correct=True, answer_order=1),
        QuizQuestionAnswer(belongs_question_id=q1.question_id, answer_title="useRouter", is_correct=False, answer_order=2),
        QuizQuestionAnswer(belongs_question_id=q1.question_id, answer_title="useStyles", is_correct=False, answer_order=3),
        QuizQuestionAnswer(belongs_question_id=q2.question_id, answer_title="false", is_correct=True, answer_order=1),
        QuizQuestionAnswer(belongs_question_id=q2.question_id, answer_title="true", is_correct=False, answer_order=2),
    ])
    db.commit()
    print("quiz created:", quiz.id)
else:
    print("quiz exists:", quiz.id)

assignment = db.query(Assignment).filter(Assignment.title == "Portfolio Landing Page").first()
if not assignment:
    assignment = Assignment(
        course_id=COURSE_ID,
        created_by=instructor.id,
        title="Portfolio Landing Page",
        description="Build and describe a single-page portfolio site.",
        total_points=100,
        submission_type="text",
        status="published",
        late_policy="penalty",
        late_penalty_pct=10,
        rubric=[
            {"criterion": "Layout & responsiveness", "max_points": 40},
            {"criterion": "Code quality", "max_points": 30},
            {"criterion": "Write-up clarity", "max_points": 30},
        ],
    )
    db.add(assignment)
    db.commit()
    print("assignment created:", assignment.id)
else:
    print("assignment exists:", assignment.id)

# ---- student actions through the real API ----
s = requests.Session()
login = s.post(f"{BASE}/auth/login", json={"email": "arjun@sashademo.com", "password": "Demo@1234"}).json()
s.headers["Authorization"] = "Bearer " + login["access_token"]

r = s.post(f"{BASE}/courses/{COURSE_ID}/quizzes/{quiz.id}/submit", json={"answers": {
    str(db.query(QuizQuestion).filter_by(quiz_id=quiz.id, question_order=1).first().question_id): 0,
    str(db.query(QuizQuestion).filter_by(quiz_id=quiz.id, question_order=2).first().question_id): "false",
    str(db.query(QuizQuestion).filter_by(quiz_id=quiz.id, question_order=3).first().question_id):
        "REST models resources as URLs with fixed verbs; GraphQL exposes one endpoint with a typed query language letting clients shape responses.",
}})
print("quiz submit:", r.status_code, r.json().get("attempt_status", r.text[:120]))

r = s.post(f"{BASE}/assignments/{assignment.id}/submit", json={
    "textContent": "Live demo: https://arjun.dev — built with React + Tailwind, deployed on Vercel. Write-up attached inline.",
    "files": [],
})
print("assignment submit:", r.status_code)

r = s.get(f"{BASE}/gamification/me")
me = r.json()
print("arjun XP:", me.get("stats", me).get("total_xp") if isinstance(me, dict) else me)
