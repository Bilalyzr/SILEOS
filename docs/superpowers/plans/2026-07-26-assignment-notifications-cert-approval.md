# Assignment Notifications + Certificate Approval Gate — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Notify instructors (in-app + email) when a student submits an assignment, and issue certificates only after an instructor or admin approves all of a course's assignment submissions.

**Architecture:** Add a new `Notification` table + read/mark-read API + a dashboard bell (in-app channel), with a best-effort email fan-out. Reuse the existing grade/return submission endpoints as the approve/reject actions, widen their auth to admins, and gate `issue_certificate_for_enrollment` on all course assignments being `GRADED`. An admin approvals queue surfaces pending submissions for fallback action.

**Tech Stack:** FastAPI + SQLAlchemy (sync) + PostgreSQL; React 18 + TypeScript + Vite; axios + React Query; TailwindCSS.

## Global Constraints

- Backend models are created by `init_db()` in `app/core/database.py` (called from `main.py` lifespan) — no Alembic. A new model must be imported before `init_db()` runs so its table is created.
- Sync SQLAlchemy session via `Depends(get_db)`; models live in `app/models/`, routers in `app/routers/` mounted under `/api/v1/...` in `app/main.py`.
- Email helpers live in `app/utils/email.py`; prod SMTP is unreliable — email is **best-effort** (backgrounded, never raises into the request). In-app notification is the source of truth.
- `SubmissionStatus` enum values are exactly `submitted`, `graded`, `returned` (`app/models/assignment.py`).
- Frontend: path aliases `@/...`; admin nav is `app/components/dashboard/nav-configs.ts`; admin pages under `frontend/src/pages/admin/`; routes in `frontend/src/App.tsx` wrapped in `<ProtectedRoute requiredRole="admin"><AdminLayout>...`.
- No test suite exists. Pure logic gets a pytest unit test under `backend/tests/`; DB/router/frontend changes are verified with the documented curl / `npx tsc` commands.
- Commit messages: imperative subject ≤ 100 chars, no co-author trailer.

---

## File Structure

**Backend**
- Create `app/models/notification.py` — `Notification` row.
- Modify `app/models/__init__.py` — import `Notification` so `init_db()` creates the table.
- Create `app/services/notification_service.py` — `create_notification(...)` (+ email fan-out).
- Create `app/routers/notifications.py` — `GET /`, `PATCH /{id}/read`, `POST /read-all`.
- Modify `app/main.py` — include the notifications router.
- Modify `app/services/certificate_service.py` — add `assignments_all_approved` (pure) + `course_assignment_approval` (DB) + gate inside `issue_certificate_for_enrollment`.
- Modify `app/routers/assignments.py` — notify on submit; widen grade/return auth to admin; trigger cert + notify on approve; notify on return.
- Modify `app/routers/admin.py` — `GET /admin/pending-submissions`.
- Create `backend/tests/test_assignment_approval.py` — unit tests for the pure predicate.
- Create `backend/tests/__init__.py` and `backend/tests/conftest.py`.

**Frontend**
- Create `frontend/src/api/notifications.ts` — API wrapper.
- Create `frontend/src/components/notifications/NotificationBell.tsx` — bell + dropdown.
- Modify the instructor & admin dashboard headers to render `<NotificationBell />`.
- Create `frontend/src/pages/admin/approvals.tsx` — pending submissions queue.
- Modify `frontend/src/App.tsx` — add `/admin/approvals` route.
- Modify `frontend/src/components/dashboard/nav-configs.ts` — add "Approvals" admin entry.
- Modify `frontend/src/pages/course-detail.tsx` — show "Certificate pending approval" state.

---

## Task 1: Notification model + table

**Files:**
- Create: `backend/app/models/notification.py`
- Modify: `backend/app/models/__init__.py`

**Interfaces:**
- Produces: `Notification` model with columns `id, user_id, type, title, message, link, related_id, is_read, created_at`.

- [ ] **Step 1: Create the model**

`backend/app/models/notification.py`:
```python
from sqlalchemy import Column, Integer, String, Text, Boolean, DateTime, ForeignKey, Index
from sqlalchemy.sql import func
from app.core.database import Base


class Notification(Base):
    __tablename__ = "notifications"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    type = Column(String(50), nullable=False)          # submission_received | cert_issued | submission_returned
    title = Column(String(255), nullable=False)
    message = Column(Text, default="")
    link = Column(String(255), nullable=True)          # frontend path, e.g. /admin/approvals
    related_id = Column(Integer, nullable=True)         # e.g. submission id
    is_read = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    __table_args__ = (Index("ix_notifications_user_unread", "user_id", "is_read"),)
```

- [ ] **Step 2: Register the model for table creation**

In `backend/app/models/__init__.py`, add an import so `init_db()` sees it (match the existing import style in that file):
```python
from app.models.notification import Notification  # noqa: F401
```

- [ ] **Step 3: Verify the table is created**

Run:
```bash
docker compose restart backend
sleep 4
docker exec -t sasha_lms-postgres-1 psql -U tutor -d tutor_lms -c "\d notifications"
```
Expected: the `notifications` table prints with the columns above.

- [ ] **Step 4: Commit**
```bash
git add backend/app/models/notification.py backend/app/models/__init__.py
git commit -m "Add Notification model and notifications table"
```

---

## Task 2: Pure approval predicate + unit test

**Files:**
- Modify: `backend/app/services/certificate_service.py`
- Create: `backend/tests/__init__.py`, `backend/tests/conftest.py`, `backend/tests/test_assignment_approval.py`

**Interfaces:**
- Produces: `assignments_all_approved(all_assignment_ids: set[int], graded_assignment_ids: set[int]) -> bool` — pure, no DB. True when every assignment id has a graded submission (and trivially true when there are no assignments).

- [ ] **Step 1: Write the failing test**

`backend/tests/__init__.py`: (empty file)

`backend/tests/conftest.py`:
```python
import os, sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
```

`backend/tests/test_assignment_approval.py`:
```python
from app.services.certificate_service import assignments_all_approved


def test_no_assignments_is_approved():
    assert assignments_all_approved(set(), set()) is True


def test_all_graded_is_approved():
    assert assignments_all_approved({1, 2, 3}, {1, 2, 3}) is True


def test_one_ungraded_is_not_approved():
    assert assignments_all_approved({1, 2, 3}, {1, 2}) is False


def test_extra_graded_ids_ignored():
    assert assignments_all_approved({1, 2}, {1, 2, 9}) is True
```

- [ ] **Step 2: Run it, verify failure**

Run: `docker exec -t sasha_lms-backend-1 python -m pytest tests/test_assignment_approval.py -v`
Expected: FAIL — `ImportError: cannot import name 'assignments_all_approved'`.

- [ ] **Step 3: Implement the pure predicate**

Add to `backend/app/services/certificate_service.py` (module level, near the top helpers):
```python
def assignments_all_approved(all_assignment_ids: set, graded_assignment_ids: set) -> bool:
    """True if every assignment id has a graded submission.

    Pure/DB-free so it is unit-testable. No assignments -> trivially True.
    """
    return set(all_assignment_ids).issubset(set(graded_assignment_ids))
```

- [ ] **Step 4: Run it, verify pass**

Run: `docker exec -t sasha_lms-backend-1 python -m pytest tests/test_assignment_approval.py -v`
Expected: 4 passed.

- [ ] **Step 5: Commit**
```bash
git add backend/app/services/certificate_service.py backend/tests
git commit -m "Add pure assignments_all_approved predicate with tests"
```

---

## Task 3: DB approval check + certificate gate

**Files:**
- Modify: `backend/app/services/certificate_service.py`

**Interfaces:**
- Consumes: `assignments_all_approved` (Task 2); `Assignment`, `AssignmentSubmission`, `SubmissionStatus` from `app.models.assignment`.
- Produces: `course_assignments_approved(db, user_id: int, course_id: int) -> bool`. Called inside `issue_certificate_for_enrollment` to block issuance until approved.

- [ ] **Step 1: Add the DB approval check**

Add to `certificate_service.py`:
```python
def course_assignments_approved(db, user_id: int, course_id: int) -> bool:
    """True if every assignment in the course has a GRADED submission by the user."""
    from app.models.assignment import Assignment, AssignmentSubmission, SubmissionStatus
    all_ids = {a.id for a in db.query(Assignment.id).filter(Assignment.course_id == course_id).all()}
    if not all_ids:
        return True
    graded_ids = {
        s.assignment_id for s in db.query(AssignmentSubmission.assignment_id).filter(
            AssignmentSubmission.user_id == user_id,
            AssignmentSubmission.assignment_id.in_(all_ids),
            AssignmentSubmission.status == SubmissionStatus.GRADED,
        ).all()
    }
    return assignments_all_approved(all_ids, graded_ids)
```
Note: `db.query(Model.column)` returns row tuples; `a.id` / `s.assignment_id` access works because a single-column query yields named tuples.

- [ ] **Step 2: Gate issuance**

In `issue_certificate_for_enrollment`, after the existing `completion_date` and "already issued" checks and after `course` is loaded (the block around `if not course: return None, False`), add:
```python
        # Gate: all course assignments must be instructor/admin-approved (GRADED).
        if not course_assignments_approved(db, enrollment.user_id, course.id):
            return None, False
```
Read the surrounding code first to place this after `course` is resolved and before the row is created.

- [ ] **Step 3: Verify gate behaves (manual, real data)**

Run (React JS course id 12 has assignments? adjust course_id to one WITH an assignment and a non-graded submission):
```bash
docker exec -i sasha_lms-backend-1 python -c "
from app.core.database import SessionLocal
from app.services.certificate_service import course_assignments_approved
db=SessionLocal()
print('approved?', course_assignments_approved(db, user_id=1, course_id=12))
"
```
Expected: prints `approved? True` when the course has no assignments or all graded; `False` when a submission is still `submitted`.

- [ ] **Step 4: Commit**
```bash
git add backend/app/services/certificate_service.py
git commit -m "Gate certificate issuance on approved assignment submissions"
```

---

## Task 4: notification_service.create_notification

**Files:**
- Create: `backend/app/services/notification_service.py`

**Interfaces:**
- Consumes: `Notification` (Task 1); `app.models.user.User`; `app.utils.email` (existing send helper).
- Produces: `create_notification(db, *, user_id, type, title, message, link=None, related_id=None, send_email=False, background_tasks=None) -> Notification`.

- [ ] **Step 1: Inspect the existing email helper**

Run: `grep -nE "^def |^async def " backend/app/utils/email.py | head`
Note the exact send function name + signature (e.g. `send_email(to, subject, body)` or an EmailService method). Use whatever exists; if none is directly callable, skip the email branch body with a `try/except` no-op and a `# TODO wire email` — but prefer the real function.

- [ ] **Step 2: Implement the service**

`backend/app/services/notification_service.py`:
```python
import logging
from app.models.notification import Notification

logger = logging.getLogger(__name__)


def _send_email_safe(user_id, subject, body):
    """Best-effort email. Never raises."""
    try:
        from app.core.database import SessionLocal
        from app.models.user import User
        from app.utils.email import send_email  # adjust to the real function from Step 1
        db = SessionLocal()
        try:
            user = db.query(User).filter(User.id == user_id).first()
            if user and user.user_email:
                send_email(user.user_email, subject, body)
        finally:
            db.close()
    except Exception as exc:
        logger.warning("notification email failed for user %s: %s", user_id, exc)


def create_notification(db, *, user_id, type, title, message="",
                        link=None, related_id=None,
                        send_email=False, background_tasks=None) -> Notification:
    """Insert an in-app notification; optionally queue a best-effort email."""
    n = Notification(
        user_id=user_id, type=type, title=title, message=message,
        link=link, related_id=related_id, is_read=False,
    )
    db.add(n)
    db.commit()
    db.refresh(n)
    if send_email and background_tasks is not None:
        background_tasks.add_task(_send_email_safe, user_id, title, message)
    return n
```
If Step 1 found no usable `send_email`, replace the import + call accordingly (match the real helper).

- [ ] **Step 3: Verify it inserts**

Run:
```bash
docker exec -i sasha_lms-backend-1 python -c "
from app.core.database import SessionLocal
from app.services.notification_service import create_notification
db=SessionLocal()
n=create_notification(db, user_id=1116, type='test', title='hello', message='world', link='/x')
print('created', n.id, n.user_id, n.title)
"
docker exec -t sasha_lms-postgres-1 psql -U tutor -d tutor_lms -c "SELECT id,user_id,type,title,is_read FROM notifications ORDER BY id DESC LIMIT 1;"
```
Expected: prints the created row; psql shows it with `is_read = f`.

- [ ] **Step 4: Commit**
```bash
git add backend/app/services/notification_service.py
git commit -m "Add notification_service.create_notification with best-effort email"
```

---

## Task 5: Notifications read API

**Files:**
- Create: `backend/app/routers/notifications.py`
- Modify: `backend/app/main.py`

**Interfaces:**
- Consumes: `Notification` (Task 1); `AuthService.get_current_active_user`; `get_db`.
- Produces: `GET /api/v1/notifications` → `{ notifications: [...], unread_count: int }`; `PATCH /api/v1/notifications/{id}/read`; `POST /api/v1/notifications/read-all`.

- [ ] **Step 1: Implement the router**

`backend/app/routers/notifications.py`:
```python
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.services.auth_service import AuthService
from app.models.user import User
from app.models.notification import Notification

router = APIRouter()


@router.get("/")
async def list_notifications(
    limit: int = Query(30, le=100),
    current_user: User = Depends(AuthService.get_current_active_user),
    db: Session = Depends(get_db),
):
    rows = (db.query(Notification)
            .filter(Notification.user_id == current_user.id)
            .order_by(Notification.created_at.desc())
            .limit(limit).all())
    unread = (db.query(Notification)
              .filter(Notification.user_id == current_user.id, Notification.is_read == False)  # noqa: E712
              .count())
    return {
        "unread_count": unread,
        "notifications": [
            {"id": n.id, "type": n.type, "title": n.title, "message": n.message,
             "link": n.link, "related_id": n.related_id, "is_read": n.is_read,
             "created_at": n.created_at}
            for n in rows
        ],
    }


@router.patch("/{notification_id}/read")
async def mark_read(
    notification_id: int,
    current_user: User = Depends(AuthService.get_current_active_user),
    db: Session = Depends(get_db),
):
    n = db.query(Notification).filter(
        Notification.id == notification_id, Notification.user_id == current_user.id).first()
    if not n:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Notification not found")
    n.is_read = True
    db.commit()
    return {"message": "marked read"}


@router.post("/read-all")
async def mark_all_read(
    current_user: User = Depends(AuthService.get_current_active_user),
    db: Session = Depends(get_db),
):
    db.query(Notification).filter(
        Notification.user_id == current_user.id, Notification.is_read == False).update(  # noqa: E712
        {Notification.is_read: True})
    db.commit()
    return {"message": "all marked read"}
```

- [ ] **Step 2: Mount the router**

In `backend/app/main.py`, next to the other `app.include_router(...)` lines, add (match the import block near the top for router imports):
```python
from app.routers import notifications as notifications_router
app.include_router(notifications_router.router, prefix="/api/v1/notifications", tags=["Notifications"])
```

- [ ] **Step 3: Verify the endpoints**

Run:
```bash
docker compose restart backend; sleep 4
TOKEN=$(curl -s -X POST http://localhost:8000/api/v1/auth/login -H "Content-Type: application/json" -d '{"email":"admin@sashainfinity.com","password":"SashaAdmin2024"}' | python -c "import sys,json;print(json.load(sys.stdin)['access_token'])")
curl -s http://localhost:8000/api/v1/notifications/ -H "Authorization: Bearer $TOKEN" | python -m json.tool | head
```
Expected: JSON with `unread_count` and a `notifications` array.

- [ ] **Step 4: Commit**
```bash
git add backend/app/routers/notifications.py backend/app/main.py
git commit -m "Add notifications read/mark-read API"
```

---

## Task 6: Notify instructor on assignment submission

**Files:**
- Modify: `backend/app/routers/assignments.py`

**Interfaces:**
- Consumes: `create_notification` (Task 4); `Assignment`, `Course`.
- Produces: on new submission and on resubmission, a `submission_received` notification for the course instructor.

- [ ] **Step 1: Add BackgroundTasks + helper import**

At the top of `assignments.py` ensure imports:
```python
from fastapi import BackgroundTasks
from app.services.notification_service import create_notification
from app.models.course import Course
```
Add `background_tasks: BackgroundTasks` to the `submit_assignment` signature (after `submission_data: dict`).

- [ ] **Step 2: Notify after both submit paths**

In `submit_assignment`, after the resubmission `db.commit()` (the RETURNED branch) and after the new-submission `db.commit()`/`db.refresh(new_submission)`, insert a shared notify call before each `return`:
```python
        assignment = db.query(Assignment).filter(Assignment.id == assignment_id).first()
        course = db.query(Course).filter(Course.id == assignment.course_id).first() if assignment else None
        if course:
            create_notification(
                db, user_id=course.post_author,
                type="submission_received",
                title="New assignment submission",
                message=f"{current_user.display_name} submitted '{assignment.title}'.",
                link="/instructor/assignments",
                related_id=(existing.id if 'existing' in dir() else new_submission.id),
                send_email=True, background_tasks=background_tasks,
            )
```
Simpler and less error-prone: compute `submission_id` in each branch and pass it. In the RETURNED branch use `existing.id`; in the new branch use `new_submission.id`. Place the notify call in each branch right before its `return` with the correct id.

- [ ] **Step 3: Verify (manual)**

Run a submit as a student (or simulate) and check a notification row is created for the instructor:
```bash
docker exec -t sasha_lms-postgres-1 psql -U tutor -d tutor_lms -c "SELECT id,user_id,type,title FROM notifications WHERE type='submission_received' ORDER BY id DESC LIMIT 3;"
```
Expected: a row addressed to the course's `post_author` after a submission.

- [ ] **Step 4: Commit**
```bash
git add backend/app/routers/assignments.py
git commit -m "Notify instructor on assignment submission"
```

---

## Task 7: Admin-fallback approve/reject + cert trigger + student notify

**Files:**
- Modify: `backend/app/routers/assignments.py`

**Interfaces:**
- Consumes: `create_notification`; `CertificateService.issue_certificate_for_enrollment`; `Enrollment`.
- Produces: `grade_submission` and `return_submission` accept instructor-who-owns-course OR admin; approving the last pending submission issues the certificate and notifies the student.

- [ ] **Step 1: Widen auth on grade + return**

`grade_submission` and `return_submission` currently `Depends(AuthService.require_instructor)`. Change both to `Depends(AuthService.get_current_active_user)` and add an explicit ownership/admin check inside each, after loading the submission's assignment + course:
```python
    assignment = db.query(Assignment).filter(Assignment.id == submission.assignment_id).first()
    course = db.query(Course).filter(Course.id == assignment.course_id).first() if assignment else None
    if not course or (course.post_author != current_user.id and current_user.role != "admin"):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not allowed to review this submission")
```
Read each handler first to reuse any submission/assignment objects already loaded.

- [ ] **Step 2: On approve (grade), try to issue the cert + notify student**

At the end of `grade_submission`, after the submission is set to `GRADED` and committed:
```python
    from app.models.enrollment import Enrollment
    from app.services.certificate_service import CertificateService
    enrollment = db.query(Enrollment).filter(
        Enrollment.user_id == submission.user_id,
        Enrollment.course_id == course.id,
        Enrollment.completion_date.isnot(None),
    ).first()
    if enrollment:
        cert, newly = CertificateService.issue_certificate_for_enrollment(db, enrollment)
        if cert and newly:
            create_notification(
                db, user_id=submission.user_id, type="cert_issued",
                title="Certificate issued",
                message=f"Your certificate for '{course.post_title}' is ready.",
                link=f"/courses/{course.post_name or course.id}/certificate",
                related_id=cert.id, send_email=True, background_tasks=background_tasks,
            )
```
Add `background_tasks: BackgroundTasks` to `grade_submission`'s signature.

- [ ] **Step 3: On return (reject), notify student**

At the end of `return_submission`, after committing the `RETURNED` status:
```python
    create_notification(
        db, user_id=submission.user_id, type="submission_returned",
        title="Assignment returned",
        message=f"Your submission for '{assignment.title}' needs changes. Please resubmit.",
        link="/dashboard", related_id=submission.id,
        send_email=True, background_tasks=background_tasks,
    )
```
Add `background_tasks: BackgroundTasks` to `return_submission`'s signature.

- [ ] **Step 4: Verify (manual)**

Run: grade the last pending submission for a completed enrollment as admin; confirm a `cert_issued` notification and an issued certificate row appear. Confirm a non-owner instructor gets 403, admin succeeds.
```bash
docker exec -t sasha_lms-postgres-1 psql -U tutor -d tutor_lms -c "SELECT type,user_id,title FROM notifications WHERE type IN ('cert_issued','submission_returned') ORDER BY id DESC LIMIT 3;"
```

- [ ] **Step 5: Commit**
```bash
git add backend/app/routers/assignments.py
git commit -m "Allow admin approve/reject; issue cert and notify student on approval"
```

---

## Task 8: Admin pending-submissions endpoint

**Files:**
- Modify: `backend/app/routers/admin.py`

**Interfaces:**
- Consumes: `AssignmentSubmission`, `Assignment`, `Course`, `User`, `SubmissionStatus`.
- Produces: `GET /api/v1/admin/pending-submissions` → list of `{ submission_id, student_name, course_title, assignment_title, submitted_at, blocks_certificate }` for all `SUBMITTED` submissions.

- [ ] **Step 1: Implement the endpoint**

Add to `admin.py` (admin-guarded like the other routes there):
```python
@router.get("/pending-submissions")
async def pending_submissions(
    current_user: User = Depends(AuthService.require_admin),
    db: Session = Depends(get_db),
):
    from app.models.assignment import Assignment, AssignmentSubmission, SubmissionStatus
    from app.models.enrollment import Enrollment
    subs = db.query(AssignmentSubmission).filter(
        AssignmentSubmission.status == SubmissionStatus.SUBMITTED).all()
    out = []
    for s in subs:
        a = db.query(Assignment).filter(Assignment.id == s.assignment_id).first()
        c = db.query(Course).filter(Course.id == a.course_id).first() if a else None
        enr = db.query(Enrollment).filter(
            Enrollment.user_id == s.user_id,
            Enrollment.course_id == (c.id if c else -1),
            Enrollment.completion_date.isnot(None)).first() if c else None
        out.append({
            "submission_id": s.id,
            "student_name": s.student.display_name if s.student else "Unknown",
            "course_title": c.post_title if c else "Unknown",
            "assignment_title": a.title if a else "Unknown",
            "submitted_at": s.submitted_at.isoformat() if s.submitted_at else None,
            "blocks_certificate": enr is not None,
        })
    return {"submissions": out}
```

- [ ] **Step 2: Verify**

Run:
```bash
TOKEN=$(curl -s -X POST http://localhost:8000/api/v1/auth/login -H "Content-Type: application/json" -d '{"email":"admin@sashainfinity.com","password":"SashaAdmin2024"}' | python -c "import sys,json;print(json.load(sys.stdin)['access_token'])")
curl -s http://localhost:8000/api/v1/admin/pending-submissions -H "Authorization: Bearer $TOKEN" | python -m json.tool | head
```
Expected: `{"submissions": [...]}` (possibly empty if nothing pending).

- [ ] **Step 3: Commit**
```bash
git add backend/app/routers/admin.py
git commit -m "Add admin pending-submissions endpoint"
```

---

## Task 9: Frontend notifications API + bell

**Files:**
- Create: `frontend/src/api/notifications.ts`
- Create: `frontend/src/components/notifications/NotificationBell.tsx`
- Modify: instructor dashboard header + admin dashboard header (locate the shared dashboard header/topbar component; render `<NotificationBell />` there).

**Interfaces:**
- Consumes: `GET/PATCH/POST /api/v1/notifications*` (Task 5); shared axios instance `@/api/axios`.
- Produces: `notificationsApi` with `list()`, `markRead(id)`, `markAllRead()`; `<NotificationBell />` component.

- [ ] **Step 1: API wrapper**

`frontend/src/api/notifications.ts`:
```typescript
import { api } from '@/api/axios'

export interface AppNotification {
  id: number; type: string; title: string; message: string
  link: string | null; related_id: number | null; is_read: boolean; created_at: string
}

export const notificationsApi = {
  list: async (): Promise<{ unread_count: number; notifications: AppNotification[] }> =>
    (await api.get('/notifications/')).data,
  markRead: async (id: number) => (await api.patch(`/notifications/${id}/read`)).data,
  markAllRead: async () => (await api.post('/notifications/read-all')).data,
}
```

- [ ] **Step 2: Bell component**

`frontend/src/components/notifications/NotificationBell.tsx`:
```tsx
import React from 'react'
import { Link } from 'react-router-dom'
import { Bell } from 'lucide-react'
import { notificationsApi, AppNotification } from '@/api/notifications'

export const NotificationBell: React.FC = () => {
  const [open, setOpen] = React.useState(false)
  const [items, setItems] = React.useState<AppNotification[]>([])
  const [unread, setUnread] = React.useState(0)

  const load = React.useCallback(async () => {
    try {
      const d = await notificationsApi.list()
      setItems(d.notifications); setUnread(d.unread_count)
    } catch { /* ignore */ }
  }, [])

  React.useEffect(() => {
    load()
    const t = setInterval(load, 60000)
    return () => clearInterval(t)
  }, [load])

  const onOpen = async () => {
    setOpen(o => !o)
    if (!open && unread > 0) { await notificationsApi.markAllRead(); setUnread(0) }
  }

  return (
    <div className="relative">
      <button onClick={onOpen} className="relative p-2 rounded-lg hover:bg-gray-100" aria-label="Notifications">
        <Bell className="w-5 h-5 text-gray-600" />
        {unread > 0 && (
          <span className="absolute -top-0.5 -right-0.5 min-w-[18px] h-[18px] px-1 rounded-full bg-red-600 text-white text-[10px] font-bold flex items-center justify-center">
            {unread > 9 ? '9+' : unread}
          </span>
        )}
      </button>
      {open && (
        <div className="absolute right-0 mt-2 w-80 max-h-96 overflow-y-auto bg-white rounded-lg shadow-lg border border-gray-200 z-50">
          <div className="px-4 py-2 text-sm font-semibold text-gray-700 border-b">Notifications</div>
          {items.length === 0 ? (
            <div className="px-4 py-8 text-center text-sm text-gray-500">No notifications</div>
          ) : items.map(n => (
            <Link key={n.id} to={n.link || '#'} onClick={() => setOpen(false)}
              className={`block px-4 py-3 text-sm border-b hover:bg-gray-50 ${n.is_read ? 'text-gray-600' : 'text-gray-900 bg-blue-50/40'}`}>
              <div className="font-medium">{n.title}</div>
              <div className="text-xs text-gray-500 line-clamp-2">{n.message}</div>
            </Link>
          ))}
        </div>
      )}
    </div>
  )
}
```

- [ ] **Step 3: Render the bell in the dashboard headers**

Run `grep -rln "DashboardNavbar\|dashboard.*header\|topbar" frontend/src/components/dashboard frontend/src/components/layout` to locate the shared dashboard top bar used by instructor + admin layouts. Import and render `<NotificationBell />` in that top bar (near the user avatar/profile menu). If instructor and admin use different headers, add it to both.

- [ ] **Step 4: Verify**

Run: `cd frontend && npx tsc --noEmit 2>&1 | grep -E "notifications|NotificationBell" | head` — expect no errors from the new files. Then load the instructor/admin dashboard in the browser and confirm the bell renders with the unread badge.

- [ ] **Step 5: Commit**
```bash
git add frontend/src/api/notifications.ts frontend/src/components/notifications/NotificationBell.tsx frontend/src/components/dashboard frontend/src/components/layout
git commit -m "Add notification bell to instructor and admin dashboards"
```

---

## Task 10: Admin approvals queue page

**Files:**
- Create: `frontend/src/pages/admin/approvals.tsx`
- Modify: `frontend/src/App.tsx`, `frontend/src/components/dashboard/nav-configs.ts`

**Interfaces:**
- Consumes: `GET /admin/pending-submissions` (Task 8); `POST /submissions/{id}/grade` and `/submissions/{id}/return` (Task 7) via `@/api/axios`.
- Produces: `AdminApprovals` page at `/admin/approvals`.

- [ ] **Step 1: Build the page**

`frontend/src/pages/admin/approvals.tsx`:
```tsx
import React from 'react'
import { api } from '@/api/axios'
import toast from 'react-hot-toast'
import { CheckCircle, RotateCcw, Award } from 'lucide-react'

interface PendingSub {
  submission_id: number; student_name: string; course_title: string
  assignment_title: string; submitted_at: string | null; blocks_certificate: boolean
}

export const AdminApprovals: React.FC = () => {
  const [rows, setRows] = React.useState<PendingSub[]>([])
  const [loading, setLoading] = React.useState(true)

  const load = async () => {
    setLoading(true)
    try { setRows((await api.get('/admin/pending-submissions')).data.submissions || []) }
    catch { setRows([]) } finally { setLoading(false) }
  }
  React.useEffect(() => { load() }, [])

  const approve = async (id: number) => {
    try { await api.post(`/submissions/${id}/grade`, { grade: 100, feedback: 'Approved' }); toast.success('Approved'); load() }
    catch (e: any) { toast.error(e?.response?.data?.detail || 'Failed') }
  }
  const reject = async (id: number) => {
    try { await api.post(`/submissions/${id}/return`, { feedback: 'Please revise and resubmit' }); toast.success('Returned'); load() }
    catch (e: any) { toast.error(e?.response?.data?.detail || 'Failed') }
  }

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl font-bold text-gray-900">Approvals</h1>
        <p className="text-gray-600 mt-1">Pending assignment submissions across all courses</p>
      </div>
      <div className="bg-white rounded-lg border border-gray-200 overflow-hidden">
        <div className="overflow-x-auto">
          <table className="min-w-full divide-y divide-gray-200">
            <thead className="bg-gray-50">
              <tr>{['Student','Course','Assignment','Submitted','Actions'].map(h => (
                <th key={h} className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">{h}</th>))}
              </tr>
            </thead>
            <tbody className="bg-white divide-y divide-gray-200">
              {loading ? (
                <tr><td colSpan={5} className="px-6 py-12 text-center text-gray-500">Loading…</td></tr>
              ) : rows.length === 0 ? (
                <tr><td colSpan={5} className="px-6 py-12 text-center text-gray-500">No pending submissions</td></tr>
              ) : rows.map(r => (
                <tr key={r.submission_id} className="hover:bg-gray-50">
                  <td className="px-6 py-4 whitespace-nowrap text-sm font-medium text-gray-900">{r.student_name}</td>
                  <td className="px-6 py-4 text-sm text-gray-600">{r.course_title}</td>
                  <td className="px-6 py-4 text-sm text-gray-600">
                    {r.assignment_title}
                    {r.blocks_certificate && (
                      <span className="ml-2 inline-flex items-center gap-1 text-xs text-amber-700">
                        <Award className="w-3 h-3" /> blocks certificate
                      </span>)}
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                    {r.submitted_at ? new Date(r.submitted_at).toLocaleDateString() : '—'}</td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm">
                    <div className="flex items-center gap-2">
                      <button onClick={() => approve(r.submission_id)} title="Approve"
                        className="p-2 rounded-lg text-green-600 hover:bg-green-50"><CheckCircle className="w-4 h-4" /></button>
                      <button onClick={() => reject(r.submission_id)} title="Return"
                        className="p-2 rounded-lg text-amber-600 hover:bg-amber-50"><RotateCcw className="w-4 h-4" /></button>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  )
}
```

- [ ] **Step 2: Route it**

In `frontend/src/App.tsx`, add the import next to the other admin page imports:
```tsx
import { AdminApprovals } from '@/pages/admin/approvals'
```
and a route inside the admin section (mirror the `/admin/students` route wrapping):
```tsx
<Route path="/admin/approvals" element={
  <ProtectedRoute requiredRole="admin"><AdminLayout><AdminApprovals /></AdminLayout></ProtectedRoute>
} />
```
Read an existing admin route (e.g. `/admin/students`) first and match its exact wrapper component names.

- [ ] **Step 3: Add the nav entry**

In `frontend/src/components/dashboard/nav-configs.ts`, in the admin nav array (near the `/admin/students` entry), add:
```typescript
{ kind: 'link', to: '/admin/approvals', label: 'Approvals', icon: CheckCircle },
```
Ensure `CheckCircle` is imported from `lucide-react` at the top of that file (add to the existing import if missing).

- [ ] **Step 4: Verify**

Run: `cd frontend && npx tsc --noEmit 2>&1 | grep -E "approvals|AdminApprovals" | head` — expect none. Then open `localhost:3000/admin/approvals` as admin: the queue renders; Approve issues the cert (when it's the last pending) and the row disappears; Return removes it from pending.

- [ ] **Step 5: Commit**
```bash
git add frontend/src/pages/admin/approvals.tsx frontend/src/App.tsx frontend/src/components/dashboard/nav-configs.ts
git commit -m "Add admin approvals queue page and nav entry"
```

---

## Task 11: Student "certificate pending approval" state

**Files:**
- Modify: `backend/app/routers/certificates.py` (or the course-detail response) to expose a derived status
- Modify: `frontend/src/pages/course-detail.tsx`

**Interfaces:**
- Consumes: `course_assignments_approved` (Task 3).
- Produces: a `certificate_status` value (`issued | pending_approval | not_eligible`) the frontend reads to choose the CTA.

- [ ] **Step 1: Expose the status (backend)**

In the course-detail response builder (`courses.py` `get_course`) or the certificate lookup used by course-detail, add a field the frontend can read. Minimal approach: in `get_course`, when the requester is enrolled and complete, compute:
```python
        from app.services.certificate_service import course_assignments_approved
        from app.models.certificate import IssuedCertificate  # confirm the issued-cert model/name
        cert_status = "not_eligible"
        if enrollment and enrollment.completion_date:
            issued = db.query(IssuedCertificate).filter(
                IssuedCertificate.user_id == current_user.id,
                IssuedCertificate.course_id == course.id).first()
            if issued:
                cert_status = "issued"
            elif course_assignments_approved(db, current_user.id, course.id):
                cert_status = "issued"   # eligible; will issue on request
            else:
                cert_status = "pending_approval"
```
Add `"certificate_status": cert_status` to the returned course dict. Read `get_course` first to reuse its existing enrollment lookup and confirm the issued-certificate model name/columns.

- [ ] **Step 2: Show the state (frontend)**

In `course-detail.tsx`, where the completed/enrolled CTA renders (the `isCompleted` block), when `course.certificate_status === 'pending_approval'`, render an amber notice instead of the certificate/download action:
```tsx
{isCompleted && (course as any).certificate_status === 'pending_approval' ? (
  <div className="bg-amber-50 border border-amber-200 rounded-xl p-4 text-sm text-amber-800">
    Certificate pending instructor approval. You'll be notified once your submission is approved.
  </div>
) : null}
```
Place it adjacent to the existing "Course Completed!" block; read that block first to slot it correctly and map `certificate_status` into the local course object in the fetch mapping.

- [ ] **Step 3: Verify**

Run: `cd frontend && npx tsc --noEmit 2>&1 | grep -E "course-detail.tsx" | grep -viE "TS18048|TS6133|TS2339|TS2322" | head` — expect no parse errors. Then, as a student who completed a course with an un-approved submission, confirm the course page shows "Certificate pending instructor approval"; after admin approves, it flips to the download/issued state.

- [ ] **Step 4: Commit**
```bash
git add backend/app/routers/courses.py frontend/src/pages/course-detail.tsx
git commit -m "Show certificate pending-approval state to students"
```

---

## Self-Review

**Spec coverage:**
- Notification system (model/service/router/bell) → Tasks 1,4,5,9. ✓
- Email best-effort → Task 4 (`send_email` in BackgroundTasks). ✓
- Cert gate on approval → Tasks 2,3. ✓
- Approve/reject via existing grade/return + admin fallback → Task 7. ✓
- Notify on submit / approve-issue / return → Tasks 6,7. ✓
- Admin approvals queue (endpoint + page + nav) → Tasks 8,10. ✓
- Student pending-approval display → Task 11. ✓

**Placeholder scan:** Tasks 2–5, 7 include exact code. Tasks 6, 9, 11 direct the implementer to read specific existing blocks (submit/grade/return handlers, dashboard header, get_course) before editing because exact line numbers shift; the code to insert is given verbatim. The one soft spot is Task 4 Step 1 (confirm the real email function name) — handled by an explicit inspection step with a safe fallback.

**Type consistency:** `assignments_all_approved(set, set)` (Task 2) is consumed by `course_assignments_approved(db, user_id, course_id)` (Task 3), consumed by `issue_certificate_for_enrollment` (Task 3) and Task 11. `create_notification(db, *, user_id, type, title, message, link, related_id, send_email, background_tasks)` (Task 4) is called with the same kwargs in Tasks 6 and 7. `notificationsApi.list/markRead/markAllRead` (Task 9) matches the router in Task 5. Consistent.

**Risks / confirm-at-implementation:** the issued-certificate model name (`IssuedCertificate` vs another) and the email helper signature — both flagged with inspection steps. The dashboard header component is located via grep in Task 9.
