"""Per-template game-config validation (spec §1, BINDING caps).

Instructor config JSON is UNTRUSTED input that other users' browsers will
render — validation here is a security boundary, not a convenience:
strict per-template pydantic schemas, extra="forbid" at every level, a
64KB serialized-size cap, and in-range index checks. Strings are stored
as-is (after stripping leading/trailing whitespace) and rendered as TEXT
by React's default escaping (never HTML) — see the frontend games
components.

CHARACTER vs BYTE semantics (fix round 1, F4): MAX_ITEM_STRING and
MAX_OPTION_STRING are CHARACTER counts (Python `str` length / pydantic
`max_length`), not byte counts. A 500-character string of multi-byte
UTF-8 (e.g. emoji) can serialize to several KB. The per-string caps are
NOT a byte-size guarantee — only MAX_CONFIG_BYTES (checked against the
UTF-8 encoded JSON) bounds total bytes. Do not size any downstream
byte-oriented buffer/storage off MAX_ITEM_STRING or MAX_OPTION_STRING.

`max_score` is derived, never stored: 10 x item count, uniformly.
`derive_max_score()` requires an already-validated config for the given
template (see its docstring) — it does not itself re-run full schema
validation.
"""
import json
import re

from pydantic import BaseModel, Field, StrictBool, StrictInt, ValidationError, validator
from typing import List

GAME_TEMPLATES = {"quiz_rush", "match_pairs", "drag_sort", "word_builder", "sequence"}
MAX_CONFIG_BYTES = 64 * 1024
MAX_ITEM_STRING = 500     # prompt/clue/left/right/text/name -- CHARACTERS, not bytes (see module docstring)
MAX_OPTION_STRING = 200   # CHARACTERS, not bytes (see module docstring)
WORD_BUILDER_ANSWER_RE = re.compile(r"^[A-Za-z0-9 ]{2,24}\Z")


class GameConfigError(ValueError):
    def __init__(self, detail: str):
        self.detail = detail
        super().__init__(detail)


class _Strict(BaseModel):
    class Config:
        extra = "forbid"


def _strip_and_require_nonempty(v: str) -> str:
    """F5: normalize display strings by stripping surrounding whitespace and
    rejecting a value that is empty (or whitespace-only) after stripping.
    Applied to every instructor-authored display string (prompt/clue/left/
    right/text/name/options/answer)."""
    stripped = v.strip()
    if not stripped:
        raise ValueError("must not be empty (or whitespace-only)")
    return stripped


# ---- quiz_rush -------------------------------------------------------------

class QuizRushItem(_Strict):
    prompt: str = Field(..., min_length=1, max_length=MAX_ITEM_STRING)
    options: List[str] = Field(..., min_items=2, max_items=6)
    # F1 CRITICAL: plain `int` lets pydantic v2 coerce bool/numeric strings
    # ("1", " 1 ", "01", "+1", True) into an int, silently rewriting the
    # instructor's answer key. StrictInt rejects every non-int type.
    answer_index: StrictInt

    @validator("prompt")
    def _prompt_strip(cls, v):
        return _strip_and_require_nonempty(v)

    @validator("options", each_item=True)
    def _option_len(cls, v):
        v = _strip_and_require_nonempty(v)
        if not (1 <= len(v) <= MAX_OPTION_STRING):
            raise ValueError(f"each option must be 1..{MAX_OPTION_STRING} chars")
        return v

    @validator("answer_index")
    def _answer_in_range(cls, v, values):
        options = values.get("options") or []
        if not (0 <= v < len(options)):
            raise ValueError("answer_index out of range")
        return v


class QuizRushSettings(_Strict):
    seconds_per_question: int = Field(20, ge=5, le=120)
    # F3 IMPORTANT: plain `bool` lets pydantic v2 coerce "yes"/"true"/1/0
    # into True/False. StrictBool accepts only an actual bool.
    shuffle: StrictBool = False


class QuizRushConfig(_Strict):
    items: List[QuizRushItem] = Field(..., min_items=1, max_items=50)
    settings: QuizRushSettings = QuizRushSettings()


# ---- match_pairs -----------------------------------------------------------

class MatchPairsItem(_Strict):
    left: str = Field(..., min_length=1, max_length=MAX_ITEM_STRING)
    right: str = Field(..., min_length=1, max_length=MAX_ITEM_STRING)

    @validator("left", "right")
    def _strip(cls, v):
        return _strip_and_require_nonempty(v)


class MatchPairsSettings(_Strict):
    time_limit_s: int = Field(0, ge=0, le=600)  # 0 = off


class MatchPairsConfig(_Strict):
    items: List[MatchPairsItem] = Field(..., min_items=3, max_items=12)
    settings: MatchPairsSettings = MatchPairsSettings()


# ---- drag_sort -------------------------------------------------------------

class DragSortCategory(_Strict):
    name: str = Field(..., min_length=1, max_length=MAX_ITEM_STRING)

    @validator("name")
    def _strip(cls, v):
        return _strip_and_require_nonempty(v)


class DragSortItem(_Strict):
    text: str = Field(..., min_length=1, max_length=MAX_ITEM_STRING)
    # F1 CRITICAL: StrictInt -- see QuizRushItem.answer_index above.
    category_index: StrictInt = Field(..., ge=0)

    @validator("text")
    def _strip(cls, v):
        return _strip_and_require_nonempty(v)


class DragSortSettings(_Strict):
    time_limit_s: int = Field(0, ge=0, le=600)


class DragSortConfig(_Strict):
    categories: List[DragSortCategory] = Field(..., min_items=2, max_items=5)
    items: List[DragSortItem] = Field(..., min_items=4, max_items=40)
    settings: DragSortSettings = DragSortSettings()

    @validator("items", each_item=True)
    def _category_in_range(cls, v, values):
        categories = values.get("categories") or []
        if not (0 <= v.category_index < len(categories)):
            raise ValueError("category_index out of range")
        return v


# ---- word_builder ----------------------------------------------------------

class WordBuilderItem(_Strict):
    clue: str = Field(..., min_length=1, max_length=MAX_ITEM_STRING)
    answer: str

    @validator("clue")
    def _clue_strip(cls, v):
        return _strip_and_require_nonempty(v)

    @validator("answer")
    def _answer_pattern(cls, v):
        v = _strip_and_require_nonempty(v)
        # F2 IMPORTANT: re.match(pattern + "$") matches immediately before a
        # trailing "\n" (Python `$` semantics), so "aaaa...a\n" (25 chars
        # incl. newline) was wrongly accepted by a 2..24-char pattern.
        # fullmatch anchors both ends exactly, closing that hole.
        if not WORD_BUILDER_ANSWER_RE.fullmatch(v):
            raise ValueError("answer must match ^[A-Za-z0-9 ]{2,24}$")
        return v


class WordBuilderSettings(_Strict):
    hints_allowed: int = Field(0, ge=0, le=3)


class WordBuilderConfig(_Strict):
    items: List[WordBuilderItem] = Field(..., min_items=1, max_items=20)
    settings: WordBuilderSettings = WordBuilderSettings()


# ---- sequence --------------------------------------------------------------

class SequenceItem(_Strict):
    text: str = Field(..., min_length=1, max_length=MAX_ITEM_STRING)

    @validator("text")
    def _strip(cls, v):
        return _strip_and_require_nonempty(v)


class SequenceSettings(_Strict):
    time_limit_s: int = Field(0, ge=0, le=600)
    # F3 IMPORTANT: StrictBool -- with plain `bool`, pydantic v2 coerces
    # "yes"/"true"/1 to True *before* _shuffle_always_true ever runs,
    # making that guard unable to reject the truthy-non-bool values it was
    # written for.
    shuffle: StrictBool = True

    @validator("shuffle")
    def _shuffle_always_true(cls, v):
        if v is not True:
            raise ValueError("sequence.shuffle is always true")
        return v


class SequenceConfig(_Strict):
    # Items are stored in CORRECT order; the engine shuffles at play time.
    items: List[SequenceItem] = Field(..., min_items=3, max_items=10)
    settings: SequenceSettings = SequenceSettings()


TEMPLATE_SCHEMAS = {
    "quiz_rush": QuizRushConfig,
    "match_pairs": MatchPairsConfig,
    "drag_sort": DragSortConfig,
    "word_builder": WordBuilderConfig,
    "sequence": SequenceConfig,
}


def validate_game_config(template: str, config: dict) -> dict:
    """Validate `config` against `template`'s schema. Returns the normalized
    config dict (defaults filled in). Raises GameConfigError with a
    human-readable detail on any violation. Called on create, EVERY update,
    and again at publish (spec §1: 'All limits re-validated')."""
    if template not in GAME_TEMPLATES:
        raise GameConfigError(f"Unknown template '{template}'. Allowed: {sorted(GAME_TEMPLATES)}")
    if not isinstance(config, dict):
        raise GameConfigError("config must be a JSON object")

    try:
        serialized = json.dumps(config)
    except (TypeError, ValueError):
        raise GameConfigError("config is not JSON-serializable")
    if len(serialized.encode("utf-8")) > MAX_CONFIG_BYTES:
        raise GameConfigError(f"config exceeds the {MAX_CONFIG_BYTES} byte cap")

    schema = TEMPLATE_SCHEMAS[template]
    try:
        parsed = schema(**config)
    except ValidationError as exc:
        first = exc.errors()[0]
        loc = ".".join(str(p) for p in first["loc"])
        raise GameConfigError(f"Invalid config: {loc}: {first['msg']}")
    except TypeError:
        raise GameConfigError("Invalid config structure")
    return parsed.dict()


def derive_max_score(template: str, config: dict) -> int:
    """Uniform rule (spec §1, BINDING): max_score = 10 x item count. For
    every template the item count is len(config['items']) — drag_sort
    counts ITEMS, never categories.

    HARD PRECONDITION (F7): `config` must already be a validate_game_config()
    output (or equivalently valid) for the given `template` — this function
    does not re-run full per-template schema validation, only a minimal
    guard against a mismatched template or a config with no usable items
    list. Callers MUST validate-then-derive, never derive an unvalidated
    dict."""
    if template not in GAME_TEMPLATES:
        raise GameConfigError(f"Unknown template '{template}'. Allowed: {sorted(GAME_TEMPLATES)}")
    items = config.get("items") if isinstance(config, dict) else None
    if not isinstance(items, list):
        raise GameConfigError("config has no items list")
    return 10 * len(items)
