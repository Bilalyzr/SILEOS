"""Build an isolated synthetic SaaS showroom. Never connects to a production DB.

Run: python scripts/seed_saas_demo.py --seed [--serve --port 8014]
Credentials, database and coverage report live only in .local/saas-demo/.
Provider calls are not faked as successful payments, delivery or AI responses.
"""
import argparse
from datetime import datetime, timedelta, timezone, date
import json
import os
from pathlib import Path
import runpy
import sys

ROOT = Path(__file__).resolve().parents[1]
DEMO = ROOT / ".local" / "saas-demo"


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--seed", action="store_true", required=True)
    parser.add_argument("--serve", action="store_true")
    parser.add_argument("--port", type=int, default=8014)
    args = parser.parse_args()
    if os.environ.get("ENVIRONMENT", "").lower() == "production":
        parser.error("Demo seeding is forbidden in a production process")
    if os.environ.get("DATABASE_URL") and "saas-demo" not in os.environ["DATABASE_URL"]:
        parser.error("Unset DATABASE_URL. This command owns only .local/saas-demo/campus-preview.sqlite")
    os.environ["SASHA_PREVIEW_ROOT"] = str(DEMO)
    os.environ["BACKGROUND_TASK_MODE"] = "disabled"
    os.environ["RUNTIME_METRICS_ENABLED"] = "false"
    os.environ["THREE_D_ROOT"] = str(DEMO / "models")
    os.environ["EBOOKS_DIR"] = str(DEMO / "ebooks")
    # Explicitly disable network providers before the preview module imports settings.
    for key in ("GLM_API_KEY", "GEMINI_API_KEY", "GOOGLE_API_KEY", "BUNNY_API_KEY", "BUNNY_TOKEN_AUTH_KEY",
                "FIREBASE_CREDENTIALS_PATH", "JITSI_JWT_SECRET", "INTERNAL_TOKEN", "CODE_RUNNER_TOKEN", "SENTRY_DSN"):
        os.environ[key] = ""
    scope = runpy.run_path(str(ROOT / "scripts" / "preview_campus.py"))
    from fastapi.testclient import TestClient
    from app.core.database import SessionLocal
    from app.core.security import create_access_token
    from app.models.user import User
    from app.models.institution import Institution, InstitutionMember, InstitutionBatch
    from app.models.course import Course, Lesson
    from app.models.enrollment import Enrollment
    from app.models.quiz import Quiz, QuizQuestion, QuizQuestionAnswer
    from app.models.assignment import Assignment, AssignmentStatus, AssignmentSubmission
    from app.models.payment import Order, OrderItem, Payment, OrderStatus, PaymentStatus
    from app.models.bundle import Bundle, BundleCourse
    from app.models.membership import MembershipPlan, MembershipPlanCourse
    from app.services.platform_tenant_service import provision_institution
    from app.services.runtime_service import ensure_schedules, claim, finish
    from app.models.runtime import RuntimeJob
    from sqlalchemy import inspect, text
    app = scope["app"]
    client = TestClient(app)
    coverage = []
    now = datetime.now(timezone.utc)
    marker = DEMO / "seed-complete.json"

    def api(method, path, body=None, actor=None, headers=None):
        hdr = dict(headers or {})
        if actor:
            hdr["Authorization"] = "Bearer " + create_access_token({"sub": str(actor.id)})
        response = client.request(method, "/api/v1" + path, json=body, headers=hdr)
        if response.status_code >= 400:
            raise RuntimeError(f"Demo setup failed: {method} {path}: {response.status_code}: {response.text[:400]}")
        return response.json() if response.content else {}

    with SessionLocal() as db:
        users = {u.user_email: u for u in db.query(User).all()}
        owner = users["campus-owner@example.org"]
        teacher = users["campus-teacher@example.org"]
        student = users["campus-student-0@example.org"]
        admin = users["platform-admin@example.org"]
        campus = db.query(Institution).filter_by(slug="greenwood-preview").one()
        members = {m.user_id: m for m in db.query(InstitutionMember).filter_by(institution_id=campus.id)}
        batch = db.query(InstitutionBatch).filter_by(institution_id=campus.id).first()
        base = f"/institutions/{campus.id}"
        if not campus.tenant_id:
            provision_institution(db, campus, owner)
            db.commit()
        tenant_id = campus.tenant_id
        if not marker.exists():
            courses = []
            for vertical, title in [("meiporul", "Explore Forces: an Immersive Journey"),
                                    ("seyappaduporul", "Grade 10 Science: Guided Practice"),
                                    ("utporul", "Python Foundations: Learn, Practise, Build")]:
                slug = "demo-" + vertical
                course = db.query(Course).filter_by(post_name=slug).first()
                if not course:
                    course = Course(post_author=teacher.id, post_title=title, post_name=slug,
                        post_content="<p>Synthetic showroom course. Explore lessons, assessments and instructor feedback.</p>",
                        post_status="published", course_type=vertical, course_price_type="paid", course_price=499)
                    db.add(course); db.flush()
                    lessons = []
                    for index, heading in enumerate(["Discover the concept", "Worked example", "Try it yourself"]):
                        lesson = Lesson(post_author=teacher.id, post_parent=course.id, post_title=heading,
                            post_content=f"<h2>{heading}</h2><p>Observe, predict, explain, then check your understanding.</p>",
                            post_status="publish", lesson_content_type="text", lesson_preview=index == 0, menu_order=index)
                        db.add(lesson); db.flush(); lessons.append(lesson)
                    course.course_sections_meta = json.dumps([{"id": "demo-section", "title": "Your first learning journey",
                        "lectureIds": [f"lesson-{l.id}" for l in lessons]}])
                    db.add(Enrollment(user_id=student.id, course_id=course.id, enrollment_status="enrolled"))
                    quiz = Quiz(post_author=teacher.id, post_parent=course.id, post_title="Demo concept checkpoint", post_status="publish")
                    db.add(quiz); db.flush()
                    question = QuizQuestion(quiz_id=quiz.id, question_title="Which habit best supports learning?", question_type="multiple_choice", question_mark=10)
                    db.add(question); db.flush()
                    for answer, correct in [("Explain and practise the concept", True), ("Skip every reflection", False)]:
                        db.add(QuizQuestionAnswer(belongs_question_id=question.question_id, answer_title=answer, is_correct=correct))
                    assignment = Assignment(course_id=course.id, created_by=teacher.id, title="Explain your approach",
                        description="Describe one example in your own words.", status=AssignmentStatus.PUBLISHED,
                        submission_type="text", due_date=now + timedelta(days=7))
                    db.add(assignment); db.flush()
                    db.add(AssignmentSubmission(assignment_id=assignment.id, user_id=student.id,
                        text_content="I compared two examples, checked my prediction and corrected my explanation."))
                    order = Order(user_id=student.id, order_key=f"DEMO-{vertical}", order_status=OrderStatus.COMPLETED,
                        payment_method="demo", total_amount=499, subtotal_amount=499, date_paid=now,
                        customer_note="Synthetic local demo. No money moved.")
                    db.add(order); db.flush()
                    db.add(OrderItem(order_id=order.id, course_id=course.id, order_item_name=title, subtotal=499, total=499))
                    db.add(Payment(order_id=order.id, user_id=student.id, payment_method="demo", amount=499,
                        payment_status=PaymentStatus.COMPLETED, payment_date=now, currency="INR"))
                courses.append(course)
            db.commit()
            bundle = db.query(Bundle).filter_by(slug="demo-discovery-pack").first()
            if not bundle:
                bundle = Bundle(name="Demo Discovery Pack", slug="demo-discovery-pack", bundle_price=999)
                db.add(bundle); db.flush()
                for course in courses: db.add(BundleCourse(bundle_id=bundle.id, course_id=course.id))
                plan = MembershipPlan(name="Demo monthly learning", period="monthly", price=299,
                    razorpay_plan_id="demo_not_a_gateway_plan", is_active=False,
                    description="Synthetic plan; enable only after creating a real sandbox gateway plan.")
                db.add(plan); db.flush()
                for course in courses: db.add(MembershipPlanCourse(plan_id=plan.id, course_id=course.id))
                db.commit()
            coverage.append({"feature": "Course publishing, lessons, quizzes, assignments, grading, bundles, revenue", "status": "seeded", "route": "/instructor/courses"})
            plan_list = api("GET", base + "/fees/plans", actor=owner)["items"]
            fee = next((p for p in plan_list if p["name"] == "Demo annual tuition"), None)
            if not fee:
                fee = api("POST", base + "/fees/plans", {"name": "Demo annual tuition", "academic_year": campus.academic_year,
                    "currency": "INR", "components": [{"code": "TUITION", "name": "Tuition", "amount": "3000"}],
                    "installments": [{"name": "Opening", "due_on": str(date.today() - timedelta(days=10)), "amount": "1500"},
                                     {"name": "Final", "due_on": str(date.today() + timedelta(days=30)), "amount": "1500"}]}, actor=owner)
                api("POST", base + f"/fees/plans/{fee['id']}/publish", actor=owner)
                account = api("POST", base + "/fees/assignments", {"student_member_id": members[student.id].id, "plan_id": fee["id"]}, actor=owner)
                api("POST", base + f"/fees/assignments/{account['id']}/payments", {"amount": "500", "method": "cash",
                    "received_by_member_id": members[owner.id].id, "reference": "DEMO-CASH-ONLY", "note": "Synthetic receipt; no cash collected"}, actor=owner,
                    headers={"Idempotency-Key": "saas-demo-cash-001"})
            coverage.append({"feature": "Tuition, installments, cash verification, receipts, parent balances", "status": "seeded", "route": "/institutions"})
            seed_campus_api(api, db, base, owner, teacher, student, members, batch, campus, now)
            coverage.append({"feature": "Exams, results, transport, hostel, staff leave", "status": "seeded", "route": "/institutions"})
            seed_vertical_api(api, db, teacher, admin, tenant_id, courses[-1], now)
            coverage.append({"feature": "Meiporul fleet and safety; Utporul coding challenge", "status": "seeded", "route": "/admin/operations"})
            ensure_schedules(db)
            token = claim(db, "payment_reconciliation", "synthetic-demo")
            if token:
                finish(db, "payment_reconciliation", token, TimeoutError("demo"))
            job = db.get(RuntimeJob, "payment_reconciliation")
            job.status = "dead"; job.attempts = 5; job.last_error = "SyntheticDemoTimeout"
            db.commit()
            # Never seed healthy worker heartbeats. The worker has not executed.
            marker.write_text(json.dumps({"created_at": now.isoformat(), "coverage": coverage}, indent=2), encoding="utf-8")
        else:
            coverage = json.loads(marker.read_text(encoding="utf-8"))["coverage"]
        seed_learning_extras(api, db, teacher, student, admin, base, owner, now)
        from seed_growth_demo import seed_growth
        from app.models.platform_tenant import PlatformTenantMembership
        billing_member = db.query(PlatformTenantMembership).filter_by(user_id=owner.id, role="owner", status="active").first()
        if billing_member:
            seed_growth(db, admin, owner, teacher, billing_member.tenant_id)
        table_counts = {}
        for name in inspect(db.bind).get_table_names():
            safe = '"' + name.replace('"', '""') + '"'
            table_counts[name] = db.execute(text("SELECT COUNT(*) FROM " + safe)).scalar()
    coverage.extend([
        {"feature": "Growth OS: ten service types, billing policies, invoices, leads, experiments and launch evidence", "status": "synthetic_seeded", "route": "/admin/operations?view=growth"},
        {"feature": "Roles, tours, institutions, learner insights", "status": "seeded", "route": "/login"},
        {"feature": "Bundled 3D models, virtual labs, games, live schedule, notices and published exam results", "status": "seeded", "route": "/admin/content-libraries"},
        {"feature": "Physical AR/VR devices, GeoGebra remote embeds and H5P package import", "status": "manual_asset_acceptance"},
        {"feature": "Razorpay capture/refund/webhook", "status": "requires_sandbox_provider"},
        {"feature": "Jitsi/Jibri recording, Bunny playback, transcription", "status": "requires_sandbox_provider"},
        {"feature": "AI generation, SMTP and WhatsApp delivery", "status": "requires_sandbox_provider"},
        {"feature": "Judge0 execution and worker recovery", "status": "requires_isolated_runner"},
    ])
    report = {"synthetic": True, "database": str(DEMO / "campus-preview.sqlite"),
        "credentials": str(DEMO / "campus-role-logins.json"), "coverage": coverage,
        "tables_with_data": sum(v > 0 for v in table_counts.values()), "table_counts": table_counts}
    (DEMO / "feature-coverage.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps({k: v for k, v in report.items() if k != "table_counts"}, indent=2))
    if args.serve:
        import uvicorn
        uvicorn.run(app, host="127.0.0.1", port=args.port)


def seed_campus_api(api, db, base, owner, teacher, student, members, batch, campus, now):
    # Use real services via API so balances, tenant policies and derived records agree.
    routes = api("GET", base + "/transport/routes", actor=owner)
    routes = routes.get("items", []) if isinstance(routes, dict) else routes
    if not any(r["name"] == "Demo North Loop" for r in routes):
        route = api("POST", base + "/transport/routes", {"name": "Demo North Loop", "capacity": 20,
            "vehicle_number": "DEMO-001", "driver_name": "Demo Driver", "fee_amount": "0", "currency": "INR",
            "stops": [{"name": "Learning Square", "pickup_time": "07:30", "drop_time": "16:30"}]}, actor=owner)
        api("POST", base + f"/transport/routes/{route['id']}/assignments", {"stop_id": route["stops"][0]["id"], "member_id": members[student.id].id}, actor=owner)
    blocks = api("GET", base + "/hostel/blocks", actor=owner)
    blocks = blocks.get("items", []) if isinstance(blocks, dict) else blocks
    if not any(b["name"] == "Demo Residence" for b in blocks):
        block = api("POST", base + "/hostel/blocks", {"name": "Demo Residence", "gender": "any", "fee_amount": "0",
            "warden_member_id": members[teacher.id].id, "rooms": [{"number": "101", "capacity": 2, "room_type": "double"}]}, actor=owner)
        api("POST", base + f"/hostel/rooms/{block['rooms'][0]['id']}/allocations", {"member_id": members[student.id].id}, actor=owner)
    api("PUT", base + "/staff/leave/types", {"academic_year": campus.academic_year,
        "types": [{"code": "CL", "name": "Casual leave", "annual_quota": 12}, {"code": "SL", "name": "Sick leave", "annual_quota": 8}]}, actor=owner)
    # Existing schedules/attendance come from the Campus preview; exam content is added here.
    from app.models.campus_operations import CampusTerm
    terms = [{"id": t.id} for t in db.query(CampusTerm).filter_by(institution_id=campus.id)]
    if not terms:
        term = api("POST", base + "/terms", {"name": "Demo Term", "starts_on": str(date.today() - timedelta(days=30)), "ends_on": str(date.today() + timedelta(days=150))}, actor=owner)
    else:
        term = terms[0]
    exams = api("GET", base + "/exams", actor=owner)
    exams = exams.get("items", []) if isinstance(exams, dict) else exams
    if not any(e["name"] == "Demo concept examination" for e in exams):
        exam = api("POST", base + "/exams", {"term_id": term["id"], "name": "Demo concept examination", "kind": "midterm"}, actor=owner)
        api("POST", base + f"/exams/{exam['id']}/papers", {"batch_id": batch.id, "subject": "Science", "max_marks": 100,
            "pass_marks": 35, "starts_at": (now + timedelta(days=14)).isoformat(), "duration_minutes": 60, "room": "Demo Hall"}, actor=owner)


def seed_vertical_api(api, db, teacher, admin, tenant_id, course, now):
    from app.models.coding_assessment import CodingChallenge
    if not db.query(CodingChallenge).filter_by(course_id=course.id).first():
        challenge = api("POST", f"/utporul/coding/courses/{course.id}/challenges", {"title": "Add two integers",
            "problem_statement": "Read two integers and print their sum.", "allowed_languages": ["python", "javascript"],
            "time_limit_ms": 1000, "memory_limit_mb": 128, "max_attempts": 5,
            "test_cases": [{"visibility": "sample", "input_text": "2 3\n", "expected_output": "5\n", "comparison": "trimmed", "weight": 1},
                           {"visibility": "hidden", "input_text": "40 2\n", "expected_output": "42\n", "comparison": "tokens", "weight": 1}]}, actor=teacher)
        api("POST", f"/utporul/coding/challenges/{challenge['id']}/action", {"action": "publish", "version": challenge["version"], "reason": "Synthetic demo challenge reviewed"}, actor=teacher)
    from app.models.meiporul_operations import ImmersiveLabSite
    if not db.query(ImmersiveLabSite).filter_by(code="DEMO-LAB-01").first():
        site = api("POST", "/meiporul/operations/sites", {"tenant_id": tenant_id, "code": "DEMO-LAB-01", "name": "Demo Immersive Lab",
            "room_count": 1, "headset_capacity": 12, "address": {"city": "Chennai", "note": "Synthetic demo location"}}, actor=admin)
        api("POST", f"/meiporul/operations/sites/{site['id']}/devices", {"asset_tag": "DEMO-VR-001", "serial_number": "SYNTHETIC-001", "device_type": "headset", "vendor": "Demo", "model": "Training headset"}, actor=admin)
        api("POST", f"/meiporul/operations/sites/{site['id']}/inspections", {"inspection_type": "pre_install", "status": "scheduled", "scheduled_for": (now + timedelta(days=2)).isoformat(), "checklist": [], "findings": "Synthetic inspection awaiting review"}, actor=admin)


def seed_learning_extras(api, db, teacher, student, admin, base, owner, now):
    from app.services.model_library_service import install_library
    from app.services.supplied_lab_pack import restore, SOURCE
    from app.models.course import Course, Lesson
    from app.models.game import Game
    from app.models.notification import Notification
    from app.models.live_class import LiveClass, LiveClassStatus
    from app.services.live_class_service import generate_room_name
    from app.models.campus_operations import CampusAttendance
    from app.models.institution import InstitutionBatchMember
    from app.models.campus_exams import CampusExam
    from app.services.mastery_service import set_links
    from app.models.enrollment import Enrollment
    # Checksummed bundled assets, placed inside the isolated demo storage root.
    models = install_library(db, admin)
    restore(db, SOURCE.read_bytes(), admin)
    course = db.query(Course).filter_by(post_name="demo-meiporul").one()
    from app.models.ebook import Ebook, EbookGrant
    from app.models.lab_notebook import LabNotebook
    from app.models.certificate import Certificate, CourseCertificate
    book = db.query(Ebook).filter_by(slug="demo-observe-explain-apply").first()
    if not book:
        from reportlab.pdfgen.canvas import Canvas
        private_root = DEMO / "ebooks"
        private_root.mkdir(exist_ok=True)
        path = private_root / "demo-observe-explain-apply.pdf"
        page = Canvas(str(path))
        page.setTitle("SashaInfinity demo learning guide")
        page.setFillColorRGB(0.9, 0.3, 0.05)
        page.setFont("Helvetica-Bold", 22)
        page.drawString(50, 780, "SashaInfinity | Learn by doing")
        page.setFillColorRGB(0.15, 0.15, 0.15)
        page.setFont("Helvetica", 12)
        for y, line in zip(range(730, 580, -25), ["SYNTHETIC DEMO - not a qualification or purchased publication.",
            "1. Observe: what changes when a force acts on an object?",
            "2. Explain: describe your prediction before running a trial.",
            "3. Apply: compare your prediction with the virtual lab result.",
            "Write your observations in your lab notebook."]):
            page.drawString(50, y, line)
        page.save()
        book = Ebook(owner_id=teacher.id, title="Demo: Observe, Explain, Apply", slug="demo-observe-explain-apply",
            category="guide", price_inr=0, status="published", course_id=course.id,
            description="Synthetic downloadable guide for the isolated showroom.", file_path=path.name,
            file_size_bytes=path.stat().st_size, page_count=1, concept_tags=["observe", "explain", "apply"])
        db.add(book); db.flush()
    if not db.query(EbookGrant).filter_by(ebook_id=book.id, user_id=student.id).first():
        db.add(EbookGrant(ebook_id=book.id, user_id=student.id, source="owner"))
    if not db.query(LabNotebook).filter_by(user_id=student.id, lab_slug="cbse-projectile-motion").first():
        db.add(LabNotebook(user_id=student.id, lab_slug="cbse-projectile-motion",
            prediction="A higher launch speed should increase range.", observation="Compare the next trial with the initial prediction.",
            conclusion="Synthetic starting note; add your own measured results.", trials=[]))
    template = db.query(Certificate).filter_by(post_name="demo-orange-completion").first()
    if not template:
        template = Certificate(post_author=admin.id, post_title="Demo SashaInfinity Completion", post_name="demo-orange-completion",
            post_content="Synthetic template for certificate designer testing", background_color="#fff7ed", title_font_color="#ea580c",
            is_global=True, elements_config={})
        db.add(template); db.flush()
    if not db.query(CourseCertificate).filter_by(course_id=course.id, certificate_id=template.id).first():
        db.add(CourseCertificate(course_id=course.id, certificate_id=template.id, email_to_student=False,
            required_completion_percentage=100, required_quiz_pass=True, required_assignment_pass=True))
    for title, kind, fields in [
        ("Explore a 3D object", "three_d", {"three_d_model_id": models[0]["model_id"]}),
        ("Investigate projectile motion", "virtual_lab", {"virtual_lab_sim": "cbse-projectile-motion"}),
    ]:
        if not db.query(Lesson).filter_by(post_parent=course.id, post_title=title).first():
            db.add(Lesson(post_author=teacher.id, post_parent=course.id, post_title=title,
                lesson_content_type=kind, post_status="publish", **fields))
    game = db.query(Game).filter_by(title="Demo Science Sprint", owner_id=teacher.id).first()
    if not game:
        created = api("POST", "/games", {"title": "Demo Science Sprint", "template": "quiz_rush",
            "config": {"items": [{"prompt": "What measures force?", "options": ["Newtons", "Litres"], "answer_index": 0}],
                       "settings": {"seconds_per_question": 20, "shuffle": False}}}, actor=teacher)
        api("POST", f"/games/{created['id']}/publish", actor=teacher)
        game = db.get(Game, created["id"])
    if not db.query(Lesson).filter_by(post_parent=course.id, post_title="Play the Science Sprint").first():
        db.add(Lesson(post_author=teacher.id, post_parent=course.id, post_title="Play the Science Sprint",
                      lesson_content_type="game", game_id=game.id, post_status="publish"))
    if not db.query(LiveClass).filter_by(title="Demo live science workshop").first():
        db.add(LiveClass(course_id=course.id, instructor_id=teacher.id, title="Demo live science workshop",
            room_name=generate_room_name(), scheduled_start=now + timedelta(days=1), scheduled_end=now + timedelta(days=1, minutes=45),
            status=LiveClassStatus.SCHEDULED))
    for user, link in [(student, "/my-courses"), (teacher, "/instructor/grading-queue"), (admin, "/admin/operations?view=runtime")]:
        if not db.query(Notification).filter_by(user_id=user.id, type="demo_welcome").first():
            db.add(Notification(user_id=user.id, type="demo_welcome", title="Welcome to the Sasha demo",
                message="This workspace contains synthetic learning and operational examples. Open How it works to explore your role.", link=link))
    for demo_course in db.query(Course).filter(Course.post_name.in_(["demo-meiporul", "demo-seyappaduporul", "demo-utporul"])):
        lessons = db.query(Lesson).filter_by(post_parent=demo_course.id).order_by(Lesson.id).all()
        demo_course.course_sections_meta = json.dumps([{"id": "demo-section", "title": "Learn by doing",
            "lectureIds": [f"lesson-{l.id}" for l in lessons]}])
        for lesson in lessons:
            set_links(db, "lesson", str(lesson.id), ["observe", "explain", "apply"], user_id=teacher.id)
    db.commit()
    # Complete exam evidence through the same mark-entry and publication gates as staff.
    exams = db.query(CampusExam).filter_by(name="Demo concept examination").all()
    for exam in exams:
        if exam.status != "published":
            from app.models.campus_exams import CampusExamPaper
            for paper in db.query(CampusExamPaper).filter_by(exam_id=exam.id):
                roster = api("GET", base + f"/exams/{exam.id}/papers/{paper.id}/marks", actor=owner)
                entries = roster if isinstance(roster, list) else roster.get("entries", roster.get("rows", roster.get("students", [])))
                if not entries:
                    members = db.query(InstitutionBatchMember).filter_by(batch_id=paper.batch_id).all()
                    entries = [{"member_id": row.member_id} for row in members]
                api("PUT", base + f"/exams/{exam.id}/papers/{paper.id}/marks", {"entries": [
                    {"member_id": entry["member_id"], "marks": 58 + (index % 4) * 10, "remarks": "Synthetic demo marks"}
                    for index, entry in enumerate(entries)]}, actor=owner)
            api("POST", base + f"/exams/{exam.id}/publish", actor=owner)
    # Attendance sample for the student roster, preserving previously entered rows.
    for member in db.query(InstitutionBatchMember).all():
        for offset in range(1, 6):
            day = date.today() - timedelta(days=offset)
            if not db.query(CampusAttendance).filter_by(batch_id=member.batch_id, member_id=member.member_id, day=day).first():
                db.add(CampusAttendance(batch_id=member.batch_id, member_id=member.member_id, day=day,
                    status="absent" if (member.member_id + offset) % 7 == 0 else "present", recorded_by=teacher.id))
    db.commit()


if __name__ == "__main__":
    main()
