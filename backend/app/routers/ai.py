"""AI question generation (SILEOS blueprint §3.6 / §15).

Real Anthropic Messages-API integration — NOT a stub. Rules from the
blueprint's guardrails, implemented:
  - every call is logged as an AiJob (model, input, output, error);
  - output is a DRAFT that lands in a QUESTION BANK, never auto-published
    to a live quiz — a human pulls it into a quiz deliberately;
  - no key configured → 503 with setup guidance (never a silent fake).

Provider is a module-level function so tests monkeypatch it without
network access.
"""
import json
import os
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.sileos_pack import AiJob, QuestionBank
from app.routers.question_banks import (_validate_question_payload,
                                        _get_owned_bank)
from app.services.auth_service import AuthService
from app.services.llm_provider import (call_glm, glm_model,
                                       llm_configured, missing_key_detail)

router = APIRouter()

MAX_QUESTIONS = 20

SYSTEM_PROMPT = (
    "You are an exam-question writer for an Indian CBSE-aligned LMS. "
    "Reply with ONLY a JSON array — no prose, no markdown fences. Each "
    "element: {question_title, question_type, question_mark, options, "
    "correct_answer, answer_explanation, difficulty}. question_type is one "
    "of multiple_choice | true_false | fill_in_blanks | short_answer. "
    "multiple_choice: options = list of 4 strings, correct_answer = 0-based "
    "index. true_false: correct_answer = \"true\" or \"false\". "
    "fill_in_blanks/short_answer: correct_answer = the expected text. "
    "difficulty is easy | medium | hard."
)


def _parse_questions(text: str) -> list[dict]:
    """Tolerant JSON-array extraction (models sometimes wrap in fences)."""
    cleaned = text.strip()
    if cleaned.startswith("```"):
        cleaned = cleaned.split("```")[1]
        if cleaned.startswith("json"):
            cleaned = cleaned[4:]
    start, end = cleaned.find("["), cleaned.rfind("]")
    if start == -1 or end == -1:
        raise ValueError("model reply contains no JSON array")
    parsed = json.loads(cleaned[start:end + 1])
    if not isinstance(parsed, list):
        raise ValueError("model reply is not a JSON array")
    return parsed


@router.post("/ai/generate-questions")
def generate_questions(
    payload: dict,
    db: Session = Depends(get_db),
    current_user=Depends(AuthService.require_instructor),
):
    if not llm_configured():
        raise HTTPException(
            status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=missing_key_detail("AI generation") +
                   " Everything else (banks, validation, audit) is live.",
        )

    topic = (payload.get("topic") or "").strip()
    count = int(payload.get("count") or 5)
    if not topic:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY,
                            detail="topic is required")
    count = max(1, min(count, MAX_QUESTIONS))
    difficulty_mix = payload.get("difficulty_mix") or "mostly medium, a few easy and hard"
    types = payload.get("question_types") or "a mix of multiple_choice, true_false and fill_in_blanks"

    # Resolve/create the target bank up front so the job references it.
    bank_id = payload.get("bank_id")
    if bank_id is not None:
        _get_owned_bank(db, int(bank_id), current_user)
    else:
        bank = QuestionBank(
            instructor_id=current_user.id,
            title=f"AI Generated — {topic[:80]}",
            description=f"Draft questions generated for topic '{topic}'. "
                        "Human review required before use in quizzes.",
        )
        db.add(bank)
        db.commit()
        db.refresh(bank)
        bank_id = bank.id

    job = AiJob(
        created_by=current_user.id,
        job_type="generate_questions",
        status="pending",
        model=glm_model(),
        input_json={"topic": topic, "count": count, "bank_id": bank_id,
                    "difficulty_mix": difficulty_mix, "question_types": types},
    )
    db.add(job)
    db.commit()
    db.refresh(job)

    prompt = (
        f"Write {count} exam questions on the topic: {topic}. "
        f"Difficulty mix: {difficulty_mix}. Use these question types: {types}. "
        "Each question_mark = 1. Explanations must teach, not just state."
    )

    try:
        text = call_glm(SYSTEM_PROMPT, prompt)
        raw_questions = _parse_questions(text)
    except Exception as exc:  # noqa: BLE001 — job audit row carries the failure
        job.status = "failed"
        job.error = str(exc)[:2000]
        job.finished_at = datetime.now(timezone.utc)
        db.commit()
        raise HTTPException(
            status.HTTP_502_BAD_GATEWAY,
            detail=f"AI provider call failed: {str(exc)[:300]}",
        ) from exc

    accepted, rejected = [], []
    for item in raw_questions:
        try:
            _validate_question_payload(item)
            if not (item.get("question_title") or "").strip():
                raise ValueError("empty question_title")
            accepted.append(item)
        except HTTPException as exc:
            rejected.append({"question": str(item.get("question_title"))[:80],
                             "reason": exc.detail})
        except Exception as exc:  # noqa: BLE001
            rejected.append({"question": str(item.get("question_title"))[:80],
                             "reason": str(exc)})

    from app.models.sileos_pack import BankQuestion
    stored_ids = []
    for item in accepted:
        row = BankQuestion(
            bank_id=bank_id,
            question_title=item["question_title"].strip(),
            question_type=item["question_type"],
            question_mark=float(item.get("question_mark") or 1.0),
            options=item.get("options"),
            correct_answer=item.get("correct_answer"),
            answer_explanation=item.get("answer_explanation", ""),
            difficulty=item.get("difficulty", "medium"),
            tags=["ai-draft", f"topic:{topic[:40]}"],
        )
        db.add(row)
        db.flush()
        stored_ids.append(row.id)
    job.status = "done"
    job.output_json = {
        "accepted": len(stored_ids), "rejected": len(rejected),
        "bank_id": bank_id, "question_ids": stored_ids,
        "rejected_detail": rejected,
    }
    job.finished_at = datetime.now(timezone.utc)
    db.commit()

    return {
        "job_id": job.id,
        "bank_id": bank_id,
        "generated": len(stored_ids),
        "rejected": rejected,
        "question_ids": stored_ids,
        "note": "Drafts landed in the question bank with tag 'ai-draft' — "
                "review before pulling into a live quiz (blueprint §15: no "
                "AI output ships without human approval).",
    }


@router.get("/ai/jobs/{job_id}")
def get_job(
    job_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(AuthService.require_instructor),
):
    job = db.query(AiJob).filter(AiJob.id == job_id).first()
    if not job:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="AI job not found")
    if current_user.role != "admin" and job.created_by != current_user.id:
        raise HTTPException(status.HTTP_403_FORBIDDEN, detail="Not your AI job")
    return {
        "id": job.id,
        "job_type": job.job_type,
        "status": job.status,
        "model": job.model,
        "input": job.input_json,
        "output": job.output_json,
        "error": job.error,
        "created_at": job.created_at.isoformat() if job.created_at else None,
        "finished_at": job.finished_at.isoformat() if job.finished_at else None,
    }
