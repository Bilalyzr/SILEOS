"""3D task configs, grading and the evidence → confidence signal (v2.0 §6).

Seven task types, ALL graded on state and parameters (§6.2), so the same
answers earn the same marks whether the learner clicked a mesh anchor in the
3D viewer (T1) or picked "Region 3" from a list on a still image (T4):

  match       labels ↔ anchors                → 10 per correct pair
  identify    pick the anchor that satisfies   → 10 per prompt
  verify      claim + parameter state + path   → 5 verdict, 3 final state, 2 explored
  assemble    parts → slots                    → 10 per correct placement
  measure     numeric answer within tolerance  → 10 per question
  manipulate  parameters into target ranges    → 10 per target
  sequence    steps in correct order           → 10 per step in place

Anchors carry `position` as NORMALISED bounding-box coordinates (0..1 per
axis), so they survive the viewer's auto-fit and any model rescale (annotate
against the mesh, never screen coordinates — sasha-ilo-authoring). `region`
is the neutral name shown to learners (auto "Region N") so a label never
leaks the answer.

Same posture as game_config.py: extra="forbid", 64KB cap, strict ints,
max_score DERIVED never stored. Grading is SERVER-SIDE from submitted
answers (never a client-supplied score).
"""
from __future__ import annotations

import json
from typing import Any, Dict, List, Optional, Tuple

from pydantic import BaseModel, Field, StrictBool, StrictFloat, StrictInt, validator

TASK_TYPES = {"match", "identify", "verify", "assemble", "measure", "manipulate", "sequence"}
MAX_CONFIG_BYTES = 64 * 1024
MAX_EVIDENCE_EVENTS = 1000
EVIDENCE_TYPES = {"view", "rotate", "zoom", "reset", "param", "select", "deselect", "hesitate", "mode", "place", "order"}
MAX_STR = 300


class TaskConfigError(ValueError):
    def __init__(self, detail: str):
        super().__init__(detail)
        self.detail = detail


class _Strict(BaseModel):
    class Config:
        extra = "forbid"


def _nonempty(v: str) -> str:
    s = v.strip()
    if not s:
        raise ValueError("must not be empty")
    return s


def _ident(v: str) -> str:
    import re
    v = _nonempty(v)
    if not re.fullmatch(r"[a-z0-9][a-z0-9_-]{0,39}", v):
        raise ValueError("ids must be lowercase letters, digits, dashes or underscores (≤40)")
    return v


Number = float


class Anchor(_Strict):
    id: str
    label: str = Field(..., min_length=1, max_length=120)
    region: Optional[str] = Field(None, max_length=60)
    position: List[float] = Field(..., min_items=3, max_items=3)
    description: Optional[str] = Field(None, max_length=MAX_STR)

    _id = validator("id", allow_reuse=True)(_ident)
    _label = validator("label", allow_reuse=True)(_nonempty)

    @validator("position", each_item=True)
    def _unit(cls, v):
        if not (0.0 <= float(v) <= 1.0):
            raise ValueError("anchor position must be normalised bounding-box coordinates in 0..1")
        return float(v)


class Parameter(_Strict):
    id: str
    label: str = Field(..., min_length=1, max_length=120)
    min: float
    max: float
    step: Optional[float] = Field(None, gt=0)
    unit: Optional[str] = Field(None, max_length=20)
    default: Optional[float] = None

    _id = validator("id", allow_reuse=True)(_ident)

    @validator("max")
    def _range(cls, v, values):
        if "min" in values and v <= values["min"]:
            raise ValueError("max must be greater than min")
        return v

    @validator("default")
    def _default_in_range(cls, v, values):
        if v is not None and "min" in values and "max" in values and not (values["min"] <= v <= values["max"]):
            raise ValueError("default must lie within min..max")
        return v


class ParamRange(_Strict):
    param_id: str
    min: float
    max: float

    @validator("max")
    def _range(cls, v, values):
        if "min" in values and v < values["min"]:
            raise ValueError("range max must be ≥ min")
        return v


def _anchor_ids(values) -> set:
    return {a.id for a in (values.get("anchors") or [])}


def _unique(ids: List[str], what: str) -> None:
    if len(ids) != len(set(ids)):
        raise ValueError(f"{what} ids must be unique")


class _WithAnchors(_Strict):
    anchors: List[Anchor] = Field(..., min_items=2, max_items=40)
    intro: Optional[str] = Field(None, max_length=500)

    @validator("anchors")
    def _anchors_unique_and_named(cls, v):
        _unique([a.id for a in v], "anchor")
        for i, a in enumerate(v, 1):
            if not a.region:
                a.region = f"Region {i}"
        return v


class MatchPair(_Strict):
    label: str = Field(..., min_length=1, max_length=120)
    anchor_id: str
    _label = validator("label", allow_reuse=True)(_nonempty)


class MatchConfig(_WithAnchors):
    pairs: List[MatchPair] = Field(..., min_items=1, max_items=40)

    @validator("pairs")
    def _pairs_ok(cls, v, values):
        ids = _anchor_ids(values)
        used = [p.anchor_id for p in v]
        _unique(used, "pair anchor")
        for p in v:
            if p.anchor_id not in ids:
                raise ValueError(f"pair references unknown anchor '{p.anchor_id}'")
        return v


class IdentifyPrompt(_Strict):
    condition: str = Field(..., min_length=1, max_length=MAX_STR)
    anchor_id: str
    _cond = validator("condition", allow_reuse=True)(_nonempty)


class IdentifyConfig(_WithAnchors):
    prompts: List[IdentifyPrompt] = Field(..., min_items=1, max_items=40)

    @validator("prompts")
    def _prompts_ok(cls, v, values):
        ids = _anchor_ids(values)
        for p in v:
            if p.anchor_id not in ids:
                raise ValueError(f"prompt references unknown anchor '{p.anchor_id}'")
        return v


class _WithParameters(_Strict):
    parameters: List[Parameter] = Field(..., min_items=1, max_items=12)
    intro: Optional[str] = Field(None, max_length=500)
    anchors: List[Anchor] = Field(default_factory=list, max_items=40)

    @validator("parameters")
    def _params_unique(cls, v):
        _unique([p.id for p in v], "parameter")
        return v


def _check_param_ranges(ranges: List[ParamRange], values, what: str) -> List[ParamRange]:
    params = {p.id: p for p in (values.get("parameters") or [])}
    for r in ranges:
        p = params.get(r.param_id)
        if p is None:
            raise ValueError(f"{what} references unknown parameter '{r.param_id}'")
        if r.min < p.min or r.max > p.max:
            raise ValueError(f"{what} range for '{r.param_id}' must lie within the parameter's min..max")
    return ranges


class VerifyConfig(_WithParameters):
    claim: str = Field(..., min_length=1, max_length=MAX_STR)
    claim_holds: StrictBool
    expected_state: List[ParamRange] = Field(default_factory=list, max_items=12)
    must_explore: List[ParamRange] = Field(default_factory=list, max_items=12)
    _claim = validator("claim", allow_reuse=True)(_nonempty)

    @validator("expected_state")
    def _exp(cls, v, values):
        return _check_param_ranges(v, values, "expected_state")

    @validator("must_explore")
    def _mex(cls, v, values):
        return _check_param_ranges(v, values, "must_explore")


class Slot(_Strict):
    id: str
    label: str = Field(..., min_length=1, max_length=120)
    _id = validator("id", allow_reuse=True)(_ident)


class Part(_Strict):
    id: str
    label: str = Field(..., min_length=1, max_length=120)
    slot_id: str
    position: Optional[List[float]] = Field(None, min_items=3, max_items=3)
    _id = validator("id", allow_reuse=True)(_ident)


class AssembleConfig(_Strict):
    slots: List[Slot] = Field(..., min_items=2, max_items=40)
    parts: List[Part] = Field(..., min_items=2, max_items=40)
    intro: Optional[str] = Field(None, max_length=500)

    @validator("slots")
    def _slots_unique(cls, v):
        _unique([s.id for s in v], "slot")
        return v

    @validator("parts")
    def _parts_ok(cls, v, values):
        _unique([p.id for p in v], "part")
        slot_ids = {s.id for s in (values.get("slots") or [])}
        for p in v:
            if p.slot_id not in slot_ids:
                raise ValueError(f"part '{p.id}' targets unknown slot '{p.slot_id}'")
        return v


class MeasureQuestion(_Strict):
    prompt: str = Field(..., min_length=1, max_length=MAX_STR)
    answer: float
    tolerance: float = Field(0, ge=0)
    unit: Optional[str] = Field(None, max_length=20)
    anchor_a: Optional[str] = None
    anchor_b: Optional[str] = None
    _prompt = validator("prompt", allow_reuse=True)(_nonempty)


class MeasureConfig(_Strict):
    # anchors BEFORE questions: pydantic validates in declaration order and
    # the questions validator cross-checks anchor references.
    anchors: List[Anchor] = Field(default_factory=list, max_items=40)
    questions: List[MeasureQuestion] = Field(..., min_items=1, max_items=40)
    intro: Optional[str] = Field(None, max_length=500)

    @validator("anchors")
    def _anchors_ok(cls, v):
        _unique([a.id for a in v], "anchor")
        for i, a in enumerate(v, 1):
            if not a.region:
                a.region = f"Region {i}"
        return v

    @validator("questions")
    def _refs(cls, v, values):
        ids = {a.id for a in (values.get("anchors") or [])}
        for q in v:
            for ref in (q.anchor_a, q.anchor_b):
                if ref is not None and ref not in ids:
                    raise ValueError(f"measure question references unknown anchor '{ref}'")
        return v


class ManipulateTarget(_Strict):
    prompt: str = Field(..., min_length=1, max_length=MAX_STR)
    param_id: str
    min: float
    max: float
    _prompt = validator("prompt", allow_reuse=True)(_nonempty)


class ManipulateConfig(_WithParameters):
    targets: List[ManipulateTarget] = Field(..., min_items=1, max_items=12)

    @validator("targets")
    def _targets_ok(cls, v, values):
        params = {p.id: p for p in (values.get("parameters") or [])}
        for t in v:
            p = params.get(t.param_id)
            if p is None:
                raise ValueError(f"target references unknown parameter '{t.param_id}'")
            if t.min > t.max or t.min < p.min or t.max > p.max:
                raise ValueError(f"target range for '{t.param_id}' must lie within the parameter's min..max")
        return v


class Step(_Strict):
    id: str
    text: str = Field(..., min_length=1, max_length=MAX_STR)
    _id = validator("id", allow_reuse=True)(_ident)
    _text = validator("text", allow_reuse=True)(_nonempty)


class SequenceConfig(_Strict):
    # Stored in CORRECT order; the player shuffles.
    steps: List[Step] = Field(..., min_items=2, max_items=20)
    anchors: List[Anchor] = Field(default_factory=list, max_items=40)
    intro: Optional[str] = Field(None, max_length=500)

    @validator("steps")
    def _steps_unique(cls, v):
        _unique([s.id for s in v], "step")
        return v


TYPE_SCHEMAS = {
    "match": MatchConfig, "identify": IdentifyConfig, "verify": VerifyConfig,
    "assemble": AssembleConfig, "measure": MeasureConfig, "manipulate": ManipulateConfig,
    "sequence": SequenceConfig,
}


def validate_task_config(task_type: str, config: Any) -> dict:
    if task_type not in TASK_TYPES:
        raise TaskConfigError(f"Unknown task_type '{task_type}'. Allowed: {sorted(TASK_TYPES)}")
    if not isinstance(config, dict):
        raise TaskConfigError("config must be a JSON object")
    try:
        serialized = json.dumps(config)
    except (TypeError, ValueError):
        raise TaskConfigError("config is not JSON-serializable")
    if len(serialized.encode("utf-8")) > MAX_CONFIG_BYTES:
        raise TaskConfigError(f"config exceeds the {MAX_CONFIG_BYTES} byte cap")
    try:
        parsed = TYPE_SCHEMAS[task_type](**config)
    except ValueError as exc:
        errors = getattr(exc, "errors", None)
        if callable(errors):
            first = errors()[0]
            loc = ".".join(str(p) for p in first["loc"])
            raise TaskConfigError(f"Invalid config: {loc}: {first['msg']}")
        raise TaskConfigError(f"Invalid config: {exc}")
    except TypeError:
        raise TaskConfigError("Invalid config structure")
    return parsed.dict()


def derive_task_max_score(task_type: str, config: dict) -> int:
    c = config or {}
    if task_type == "match":
        return 10 * len(c.get("pairs") or [])
    if task_type == "identify":
        return 10 * len(c.get("prompts") or [])
    if task_type == "verify":
        return 10
    if task_type == "assemble":
        return 10 * len(c.get("parts") or [])
    if task_type == "measure":
        return 10 * len(c.get("questions") or [])
    if task_type == "manipulate":
        return 10 * len(c.get("targets") or [])
    if task_type == "sequence":
        return 10 * len(c.get("steps") or [])
    return 0


# ---------------------------------------------------------------- grading

def _num(v) -> Optional[float]:
    if isinstance(v, bool) or v is None:
        return None
    if isinstance(v, (int, float)):
        return float(v)
    try:
        return float(str(v).strip())
    except ValueError:
        return None


def _explored_ranges(evidence: List[dict]) -> Dict[str, List[float]]:
    seen: Dict[str, List[float]] = {}
    for e in evidence or []:
        if e.get("type") == "param":
            v = _num(e.get("value"))
            pid = e.get("param_id")
            if pid and v is not None:
                seen.setdefault(str(pid), []).append(v)
    return seen


def grade_task(task_type: str, config: dict, answers: Any, evidence: Optional[List[dict]] = None) -> Tuple[int, Dict[str, Any]]:
    """Return (score, detail). Never trusts a client score; grades STATE."""
    answers = answers if isinstance(answers, dict) else {}
    detail: Dict[str, Any] = {}
    if task_type == "match":
        given = answers.get("pairs") or {}
        correct = 0
        per = []
        for i, p in enumerate(config["pairs"]):
            ok = str(given.get(str(i), given.get(i))) == p["anchor_id"] if isinstance(given, dict) else False
            per.append(ok)
            correct += ok
        detail["per_pair"] = per
        return 10 * correct, detail
    if task_type == "identify":
        sel = answers.get("selections") or []
        per = []
        for i, p in enumerate(config["prompts"]):
            per.append(i < len(sel) and str(sel[i]) == p["anchor_id"])
        detail["per_prompt"] = per
        return 10 * sum(per), detail
    if task_type == "verify":
        score = 0
        verdict_ok = isinstance(answers.get("claim_holds"), bool) and answers["claim_holds"] == config["claim_holds"]
        detail["verdict_correct"] = verdict_ok
        if verdict_ok:
            score += 5
        final = answers.get("final_state") or {}
        state_ok = all(
            (_num(final.get(r["param_id"])) is not None and r["min"] <= _num(final.get(r["param_id"])) <= r["max"])
            for r in config.get("expected_state") or []
        )
        detail["final_state_ok"] = state_ok
        if state_ok:
            score += 3
        explored = _explored_ranges(evidence or [])
        tested = all(
            any(r["min"] <= v <= r["max"] for v in explored.get(r["param_id"], []))
            for r in config.get("must_explore") or []
        )
        detail["path_tested_claim"] = tested
        if tested:
            score += 2
        return score, detail
    if task_type == "assemble":
        placements = answers.get("placements") or {}
        per = {p["id"]: str(placements.get(p["id"])) == p["slot_id"] for p in config["parts"]}
        detail["per_part"] = per
        return 10 * sum(per.values()), detail
    if task_type == "measure":
        vals = answers.get("values") or []
        per = []
        for i, q in enumerate(config["questions"]):
            v = _num(vals[i]) if i < len(vals) else None
            per.append(v is not None and abs(v - float(q["answer"])) <= float(q.get("tolerance") or 0) + 1e-9)
        detail["per_question"] = per
        return 10 * sum(per), detail
    if task_type == "manipulate":
        final = answers.get("final_state") or {}
        per = []
        for t in config["targets"]:
            v = _num(final.get(t["param_id"]))
            per.append(v is not None and t["min"] <= v <= t["max"])
        detail["per_target"] = per
        return 10 * sum(per), detail
    if task_type == "sequence":
        order = [str(x) for x in (answers.get("order") or [])]
        per = [i < len(order) and order[i] == s["id"] for i, s in enumerate(config["steps"])]
        detail["per_step"] = per
        return 10 * sum(per), detail
    return 0, detail


# ---------------------------------------------------------------- evidence

def validate_evidence(evidence: Any) -> List[dict]:
    if evidence is None:
        return []
    if not isinstance(evidence, list) or len(evidence) > MAX_EVIDENCE_EVENTS:
        raise TaskConfigError(f"evidence must be a list of at most {MAX_EVIDENCE_EVENTS} events")
    out = []
    for e in evidence:
        if not isinstance(e, dict) or len(e) > 12 or e.get("type") not in EVIDENCE_TYPES:
            raise TaskConfigError("evidence events need a known 'type' and at most 12 fields")
        clean = {}
        for k, v in e.items():
            if isinstance(v, str) and len(v) > 120:
                v = v[:120]
            if isinstance(v, (str, int, float, bool)) or v is None:
                clean[str(k)[:40]] = v
        out.append(clean)
    return out


def confidence_signal(evidence: List[dict], score: int, max_score: int) -> Tuple[str, Dict[str, Any]]:
    """§6.3: was it reasoning or fumbling? Heuristic over the path."""
    resets = sum(1 for e in evidence if e.get("type") == "reset")
    wrong = sum(1 for e in evidence if e.get("type") == "select" and e.get("correct") is False)
    right = sum(1 for e in evidence if e.get("type") == "select" and e.get("correct") is True)
    params = sum(1 for e in evidence if e.get("type") == "param")
    hesitations = sum(1 for e in evidence if e.get("type") == "hesitate")
    views = sum(1 for e in evidence if e.get("type") in ("rotate", "view"))
    detail = {"resets": resets, "wrong_selections": wrong, "correct_selections": right,
              "parameter_changes": params, "hesitations": hesitations, "view_changes": views,
              "events": len(evidence)}
    if not evidence:
        return "unknown", detail
    if wrong >= 2 or resets >= 3 or (wrong >= 1 and hesitations >= 3):
        label = "trial_and_error"
    elif wrong == 0 and resets <= 1:
        label = "clean"
    else:
        label = "mixed"
    if max_score and score == max_score and label == "trial_and_error":
        detail["note"] = "correct, but the path suggests trial and error"
    return label, detail
