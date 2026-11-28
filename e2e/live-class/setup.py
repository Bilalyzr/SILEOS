import json, os, secrets
from datetime import timedelta
from app.core.database import SessionLocal
from app.core.security import create_access_token, get_password_hash
from app.models.user import User, UserProfile
from app.models.enrollment import Enrollment
from app.models.coding_assessment import CodingChallenge
db = SessionLocal()
stamp = secrets.token_hex(3)
COURSE = int(os.environ.get("LC_COURSE_ID", "23"))
challenge = db.query(CodingChallenge).filter_by(course_id=COURSE, status="published").order_by(CodingChallenge.id).first()
instr = db.query(User).filter_by(user_email=os.environ["LC_INSTRUCTOR_EMAIL"]).one()  # an existing instructor who owns the course
learner_password = secrets.token_urlsafe(12)  # throwaway students get a fresh random password each run
def student(tag, n):
    u = User(user_login=f"lcsuite-{stamp}-{tag}", user_pass=get_password_hash(learner_password), user_nicename=f"lcsuite-{tag}",
             user_email=f"lcsuite-{stamp}-{tag}@example.com", display_name=f"LC Student {tag.upper()}", role="student", is_active=True, is_verified=True)
    db.add(u); db.commit(); db.refresh(u)
    db.add(Enrollment(course_id=COURSE, user_id=u.id, enrollment_status="enrolled"))
    db.add(UserProfile(user_id=u.id, phone=f"+91987654{n:04d}")); db.commit()
    return u
a, b = student("a", 1), student("b", 2)
tok = lambda u: create_access_token(data={"sub": str(u.id)}, expires_delta=timedelta(hours=3))
json.dump({"stamp": stamp, "course": COURSE, "challenge_id": challenge.id, "challenge_slug": challenge.slug, "challenge_title": challenge.title,
  "instructor": {"id": instr.id, "email": instr.user_email, "password": os.environ["LC_INSTRUCTOR_PASSWORD"], "token": tok(instr)},
  "a": {"id": a.id, "email": a.user_email, "password": learner_password, "token": tok(a)},
  "b": {"id": b.id, "email": b.user_email, "password": learner_password, "token": tok(b)}}, open("/tmp/lc_manifest.json", "w"))
print("setup ok", stamp, "challenge", challenge.id, challenge.slug)
