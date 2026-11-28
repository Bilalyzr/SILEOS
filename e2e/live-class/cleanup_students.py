"""Remove the throwaway students the suite created (logins starting with lcsuite-) and everything they made.

Accounts that other records still reference cannot be deleted, so they are deactivated instead.
Also removes live coding pushes on the class given in LC_LIVE_CLASS_ID (used by coding_only.py), if set.
"""
import os
from sqlalchemy import text
from app.core.database import SessionLocal

db = SessionLocal()
live_class = os.environ.get("LC_LIVE_CLASS_ID")
pushes = []
if live_class:
    pushes = [r[0] for r in db.execute(text("select id from live_coding_challenges where class_id = :c"), {"c": int(live_class)})]
    db.execute(text("delete from live_coding_submissions where live_id = any(:p)"), {"p": pushes or [-1]})
    db.execute(text("delete from live_coding_challenges where id = any(:p)"), {"p": pushes or [-1]})
users = [r[0] for r in db.execute(text("select id from users where user_login like 'lcsuite-%'"))]
subs = [r[0] for r in db.execute(text("select id from coding_submissions where user_id = any(:u)"), {"u": users or [-1]})]
for table in ("coding_case_results", "coding_judge_jobs", "live_coding_submissions", "coding_review_requests"):
    db.execute(text(f"delete from {table} where submission_id = any(:s)"), {"s": subs or [-1]})
db.execute(text("delete from coding_submissions where id = any(:s)"), {"s": subs or [-1]})
for table in ("coding_drafts", "live_class_attendance", "live_class_join_tokens", "live_class_events", "enrollments", "user_profiles"):
    db.execute(text(f"delete from {table} where user_id = any(:u)"), {"u": users or [-1]})
db.commit()
deleted = 0
for uid in users:
    try:
        db.execute(text("delete from users where id = :i"), {"i": uid}); db.commit(); deleted += 1
    except Exception:
        db.rollback()
        db.execute(text("update users set is_active = false where id = :i"), {"i": uid}); db.commit()
print(f"pushes removed: {len(pushes)} | submissions removed: {len(subs)} | students deleted: {deleted} of {len(users)} (rest deactivated)")
