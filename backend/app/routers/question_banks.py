"""Question banks — reusable, tagged, difficulty-rated pools
(SILEOS blueprint §3.4, integrated backend-only).

Endpoints:
  POST   /question-banks                          create a bank
  GET    /question-banks                          list own banks (+counts)
  GET    /question-banks/{id}                     bank detail with questions
  DELETE /question-banks/{id}                     delete bank (owner)
  POST   /question-banks/{id}/questions           add one question
  POST   /question-banks/{id}/import-from-quiz/{quiz_id}
         copy a live quiz's questions into the bank (snapshot — editing the
         bank afterwards never rewrites the live quiz)
  GET    /question-banks/{id}/analysis            per-question item analysis:
         facility (p-value = share correct), discrimination (top-bottom 27%),
         attempts — the blueprint's "difficulty calibration, item analysis".

Ownership rule: instructor owns their banks; admin sees all. Students have
no bank surface (questions leak answers).
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func as sa_func
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.quiz import (Quiz, QuizAttempt, QuizAttemptAnswer,
                             QuizQuestion)
from app.models.sileos_pack import (QUESTION_BANK_TYPES,
                                    QUESTION_DIFFICULTIES, BankQuestion,
                                    QuestionBank)
from app.services.auth_service import AuthService

router = APIRouter()


def _get_owned_bank(db: Session, bank_id: int, user) -> QuestionBank:
    bank = db.query(QuestionBank).filter(QuestionBank.id == bank_id).first()
    if not bank:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Question bank not found")
    if user.role != "admin" and bank.instructor_id != user.id:
        raise HTTPException(status.HTTP_403_FORBIDDEN,
                            detail="Not your question bank")
    return bank


def _validate_question_payload(data: dict) -> None:
    qtype = data.get("question_type")
    if qtype not in QUESTION_BANK_TYPES:
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"question_type must be one of {QUESTION_BANK_TYPES}",
        )
    difficulty = data.get("difficulty", "medium")
    if difficulty not in QUESTION_DIFFICULTIES:
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"difficulty must be one of {QUESTION_DIFFICULTIES}",
        )
    if qtype in ("multiple_choice", "true_false", "fill_in_blanks") and \
            data.get("correct_answer") in (None, ""):
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="correct_answer is required for objective types",
        )
    if qtype == "multiple_choice":
        options = data.get("options") or []
        if len([o for o in options if str(o).strip()]) < 2:
            raise HTTPException(
                status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="multiple_choice needs >= 2 non-empty options",
            )
        idx = data.get("correct_answer")
        if not isinstance(idx, int) or not (0 <= idx < len(options)):
            raise HTTPException(
                status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="correct_answer must be an in-range option index",
            )


@router.post("", status_code=status.HTTP_201_CREATED)
def create_bank(
    payload: dict,
    db: Session = Depends(get_db),
    current_user=Depends(AuthService.require_instructor),
):
    title = (payload.get("title") or "").strip()
    if not title:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY,
                            detail="title is required")
    bank = QuestionBank(
        instructor_id=current_user.id,
        title=title[:200],
        description=payload.get("description", ""),
    )
    db.add(bank)
    db.commit()
    db.refresh(bank)
    return {"id": bank.id, "title": bank.title, "question_count": 0}


@router.get("")
def list_banks(
    db: Session = Depends(get_db),
    current_user=Depends(AuthService.require_instructor),
):
    rows = (
        db.query(
            QuestionBank.id,
            QuestionBank.title,
            QuestionBank.description,
            sa_func.count(BankQuestion.id).label("question_count"),
        )
        .outerjoin(BankQuestion, BankQuestion.bank_id == QuestionBank.id)
        .filter(QuestionBank.instructor_id == current_user.id)
        .group_by(QuestionBank.id)
        .order_by(QuestionBank.created_at.desc())
        .all()
    )
    return {
        "banks": [
            {"id": r.id, "title": r.title, "description": r.description,
             "question_count": r.question_count}
            for r in rows
        ]
    }


@router.get("/{bank_id}")
def get_bank(
    bank_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(AuthService.require_instructor),
):
    bank = _get_owned_bank(db, bank_id, current_user)
    return {
        "id": bank.id,
        "title": bank.title,
        "description": bank.description,
        "questions": [
            {
                "id": q.id,
                "question_title": q.question_title,
                "question_type": q.question_type,
                "question_mark": q.question_mark,
                "options": q.options,
                "difficulty": q.difficulty,
                "tags": q.tags,
                "answer_explanation": q.answer_explanation,
                "source_quiz_question_id": q.source_quiz_question_id,
            }
            for q in bank.questions
        ],
    }


@router.delete("/{bank_id}")
def delete_bank(
    bank_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(AuthService.require_instructor),
):
    bank = _get_owned_bank(db, bank_id, current_user)
    if bank.questions:
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            detail="Bank has questions — empty it first (questions may be "
                   "referenced by generated quizzes; banks with content are "
                   "never silently destroyed)",
        )
    db.delete(bank)
    db.commit()
    return {"deleted": True, "id": bank_id}


@router.post("/{bank_id}/questions")
def add_question(
    bank_id: int,
    payload: dict,
    db: Session = Depends(get_db),
    current_user=Depends(AuthService.require_instructor),
):
    bank = _get_owned_bank(db, bank_id, current_user)
    _validate_question_payload(payload)
    q = BankQuestion(
        bank_id=bank.id,
        question_title=(payload.get("question_title") or "").strip(),
        question_type=payload["question_type"],
        question_mark=float(payload.get("question_mark") or 1.0),
        options=payload.get("options"),
        correct_answer=payload.get("correct_answer"),
        answer_explanation=payload.get("answer_explanation", ""),
        difficulty=payload.get("difficulty", "medium"),
        tags=payload.get("tags") or [],
    )
    if not q.question_title:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY,
                            detail="question_title is required")
    db.add(q)
    db.commit()
    db.refresh(q)
    return {"id": q.id, "bank_id": bank.id}


@router.post("/{bank_id}/import-from-quiz/{quiz_id}")
def import_from_quiz(
    bank_id: int,
    quiz_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(AuthService.require_instructor),
):
    """Snapshot a live quiz's questions into the bank. Copies — never moves:
    the live quiz keeps working untouched (blueprint §3.4 reuse model)."""
    bank = _get_owned_bank(db, bank_id, current_user)
    quiz = db.query(Quiz).filter(Quiz.id == quiz_id).first()
    if not quiz:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Quiz not found")
    if current_user.role != "admin" and quiz.post_author != current_user.id:
        raise HTTPException(status.HTTP_403_FORBIDDEN,
                            detail="Not your quiz")
    questions = (
        db.query(QuizQuestion)
        .filter(QuizQuestion.quiz_id == quiz_id)
        .order_by(QuizQuestion.question_order)
        .all()
    )
    if not questions:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY,
                            detail="Quiz has no questions to import")

    added = []
    for q in questions:
        settings = q.question_settings or {}
        copy = BankQuestion(
            bank_id=bank.id,
            question_title=q.question_title,
            question_type=q.question_type,
            question_mark=float(q.question_mark or 1.0),
            options=settings.get("options"),
            correct_answer=settings.get("correct_answer"),
            answer_explanation=q.answer_explanation or "",
            difficulty="medium",
            tags=[f"quiz-{quiz_id}"],
            source_quiz_question_id=q.question_id,
        )
        db.add(copy)
        added.append(copy)
    db.commit()
    return {"imported": len(added), "bank_id": bank.id, "quiz_id": quiz_id}


@router.get("/{bank_id}/analysis")
def item_analysis(
    bank_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(AuthService.require_instructor),
):
    """Blueprint §3.4 item analysis, per bank question:
      - attempts: how many graded answers exist (via source provenance when
        the question came from a live quiz, else via exact-title match)
      - facility: p-value = share correct (1.0 = everyone right → too easy)
      - discrimination: (top-27% correct rate) − (bottom-27% correct rate)
        over the quiz attempts the question participated in; positive values
        separate strong from weak students (0.30+ is good).
    Computed read-only over live quiz answers — banks never store responses.
    """
    bank = _get_owned_bank(db, bank_id, current_user)
    items = []
    for q in bank.questions:
        source_qid = q.source_quiz_question_id
        # Fall back to title match for hand-added questions that mirror a
        # live quiz question (documented limitation — provenance beats guessing).
        answers_q = db.query(QuizAttemptAnswer).filter(
            QuizAttemptAnswer.question_id == (source_qid or -1)
        )
        if source_qid is None:
            live = db.query(QuizQuestion).filter(
                QuizQuestion.question_title == q.question_title
            ).first()
            answers_q = db.query(QuizAttemptAnswer).filter(
                QuizAttemptAnswer.question_id == (live.question_id if live else -1)
            )
        answers = answers_q.all()
        attempts = len(answers)
        correct = sum(1 for a in answers if a.is_correct)
        facility = round(correct / attempts, 3) if attempts else None

        discrimination = None
        if attempts >= 6:
            by_attempt: dict[int, float] = {}
            for a in answers:
                by_attempt.setdefault(a.quiz_attempt_id, 0.0)
                by_attempt[a.quiz_attempt_id] += float(a.achieved_mark or 0)
            ordered = sorted(by_attempt.items(), key=lambda kv: kv[1])
            k = max(1, int(len(ordered) * 0.27))
            weak_ids = {aid for aid, _ in ordered[:k]}
            strong_ids = {aid for aid, _ in ordered[-k:]}

            def _rate(group_ids: set) -> float:
                group_answers = [a for a in answers if a.quiz_attempt_id in group_ids]
                return (sum(1 for a in group_answers if a.is_correct)
                        / len(group_answers)) if group_answers else 0.0

            discrimination = round(_rate(strong_ids) - _rate(weak_ids), 3)

        items.append({
            "bank_question_id": q.id,
            "question_title": q.question_title,
            "difficulty": q.difficulty,
            "attempts": attempts,
            "correct_count": correct,
            "facility": facility,
            "discrimination": discrimination,
            "flag": (
                "too_easy" if facility is not None and facility > 0.95
                else "too_hard" if facility is not None and facility < 0.25
                else "weak_discrimination" if discrimination is not None and discrimination < 0.10
                else "ok" if attempts else "no_data"
            ),
        })
    return {"bank_id": bank.id, "items": items}


# ---------------------------------------------------------------- roadmap item 5: banks at scale

def _bank_to_quiz_question(db: Session, quiz_id: int, bq: BankQuestion, order: int) -> None:
    from app.models.quiz import QuizQuestion, QuizQuestionAnswer
    q = QuizQuestion(quiz_id=quiz_id, question_title=bq.question_title, question_type=bq.question_type,
                     question_mark=float(bq.question_mark or 1), answer_explanation=bq.answer_explanation or "", question_order=order,
                     question_settings={"bank_question_id": bq.id, "difficulty": bq.difficulty})
    db.add(q)
    db.flush()
    opts = bq.options if isinstance(bq.options, list) else []
    corr = bq.correct_answer
    if bq.question_type in ("multiple_choice", "multiple_select") and opts:
        correct_idx = set()
        if isinstance(corr, list):
            correct_idx = {int(c) for c in corr if str(c).isdigit()}
        elif isinstance(corr, (int, float)) or (isinstance(corr, str) and corr.isdigit()):
            correct_idx = {int(corr)}
        for i, o in enumerate(opts):
            db.add(QuizQuestionAnswer(belongs_question_id=q.question_id, belongs_question_type=bq.question_type,
                                      answer_title=str(o), is_correct=i in correct_idx, answer_order=i + 1))
    elif bq.question_type == "true_false":
        truth = str(corr).strip().lower() in ("true", "t", "1")
        db.add(QuizQuestionAnswer(belongs_question_id=q.question_id, belongs_question_type="true_false", answer_title="True", is_correct=truth, answer_order=1))
        db.add(QuizQuestionAnswer(belongs_question_id=q.question_id, belongs_question_type="true_false", answer_title="False", is_correct=not truth, answer_order=2))
    elif corr not in (None, ""):
        db.add(QuizQuestionAnswer(belongs_question_id=q.question_id, belongs_question_type=bq.question_type, answer_title=str(corr), is_correct=True, answer_order=1))


@router.post("/{bank_id}/push-to-quiz/{quiz_id}", status_code=201)
def push_to_quiz(
    bank_id: int,
    quiz_id: int,
    payload: dict,
    db: Session = Depends(get_db),
    current_user=Depends(AuthService.require_instructor),
):
    """Draw N random bank questions (optionally by difficulty mix) into a quiz
    as SNAPSHOT copies. With quiz_max_questions_for_take set, each attempt
    then gets its own random subset — randomisation from banks end to end."""
    import random
    from app.models.course import Course
    from app.models.quiz import Quiz, QuizQuestion
    from app.services.course_access import can_edit
    bank = _get_owned_bank(db, bank_id, current_user)
    quiz = db.query(Quiz).filter(Quiz.id == quiz_id).first()
    if not quiz:
        raise HTTPException(status_code=404, detail="Quiz not found")
    course = db.query(Course).filter(Course.id == quiz.post_parent).first()
    if not can_edit(db, course, current_user):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not your course")
    count = max(1, min(int(payload.get("count") or 10), 200))
    mix = payload.get("difficulty_mix") or {}
    pool = [q for q in bank.questions if not {"ai-draft", "studio-draft", "studio-retired"}.intersection(q.tags or [])]
    if not pool:
        raise HTTPException(status_code=422, detail="The bank has no reviewed questions to draw from")
    chosen = []
    if mix:
        for level in ("easy", "medium", "hard"):
            want = int(mix.get(level) or 0)
            bucket = [q for q in pool if (q.difficulty or "medium") == level]
            random.shuffle(bucket)
            chosen.extend(bucket[:want])
    remaining = [q for q in pool if q not in chosen]
    random.shuffle(remaining)
    chosen.extend(remaining[:max(0, count - len(chosen))])
    chosen = chosen[:count]
    start_order = (db.query(sa_func.max(QuizQuestion.question_order)).filter(QuizQuestion.quiz_id == quiz_id).scalar() or 0) + 1
    for i, bq in enumerate(chosen):
        _bank_to_quiz_question(db, quiz_id, bq, start_order + i)
    db.commit()
    return {"quiz_id": quiz_id, "added": len(chosen), "pool": len(pool),
            "by_difficulty": {lvl: sum(1 for q in chosen if (q.difficulty or "medium") == lvl) for lvl in ("easy", "medium", "hard")}}


@router.get("/{bank_id}/export.csv")
def export_bank_csv(
    bank_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(AuthService.require_instructor),
):
    """Same column layout the CSV importer accepts, so banks round-trip."""
    import csv
    import io
    from fastapi.responses import Response
    bank = _get_owned_bank(db, bank_id, current_user)
    buf = io.StringIO()
    w = csv.writer(buf)
    w.writerow(["question", "type", "option_a", "option_b", "option_c", "option_d", "correct", "marks", "explanation", "difficulty", "tags"])
    letters = "ABCD"
    for q in bank.questions:
        opts = q.options if isinstance(q.options, list) else []
        corr = q.correct_answer
        if q.question_type in ("multiple_choice", "multiple_select") and opts:
            idx = [int(c) for c in (corr if isinstance(corr, list) else [corr]) if str(c).isdigit()]
            correct = ",".join(letters[i] for i in idx if i < 4)
        elif q.question_type == "true_false":
            correct = "TRUE" if str(corr).strip().lower() in ("true", "t", "1") else "FALSE"
        else:
            correct = "" if corr is None else str(corr)
        padded = [str(o) for o in opts[:4]] + [""] * (4 - min(4, len(opts)))
        w.writerow([q.question_title, q.question_type, *padded, correct, q.question_mark or 1, q.answer_explanation or "",
                    q.difficulty or "medium", "|".join(q.tags or [])])
    return Response(content=buf.getvalue(), media_type="text/csv",
                    headers={"Content-Disposition": f'attachment; filename="bank-{bank.id}.csv"'})
