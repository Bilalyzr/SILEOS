# Learning Games Builder Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development.
> Dispatches point implementers at THIS file's task section + the spec
> (docs/superpowers/specs/2026-09-03-learning-games-design.md) — the spec's numbered
> sections are the requirements; task sections below add file maps, exact code, and
> sequencing. Both BINDING.

**Goal:** A native game engine + builder so instructors create concept-based learning games
themselves (no external tools), attach them to courses as lessons, and students play them with
scores, XP, and progress tracking — end to end inside Sasha. Branch `learning-games`
(worktree `.worktrees/learning-games`, forked from `revenue-platform` @ 6d937c3).

**Architecture:** One JSON `config` per game drives 5 client-side engine templates; the backend
stores/validates games (`games`, `game_results` tables, router `app/routers/games.py` at
`/api/v1/games`), gates play by publish+enrollment through the lesson attach point
(`lessons.game_id`), and re-derives `max_score` server-side. Grading is client-side for instant
feedback, so scores are advisory only and never enter the gradebook — identical posture to H5P.
XP flows through the existing event-sourced `gamification_service.award()`.

**Tech Stack:** existing only — FastAPI + SQLAlchemy + Alembic (backend), React 18 + TS + Vite +
Tailwind + `@dnd-kit` (already in frontend/package.json: `@dnd-kit/core@^6.3.1`,
`@dnd-kit/sortable@^10.0.0`, `@dnd-kit/utilities@^3.2.2`), Vitest, pytest. **No new
dependencies.** Game assets are inline SVG/CSS only.

## Global Constraints

All BINDING; every task re-checks the ones it touches.

1. **Config validation caps (spec §1, verbatim):**
   - `quiz_rush`: `items: [{prompt, options: [2..6 strings], answer_index}]` (1..50 items),
     `settings: {seconds_per_question: 5..120 (default 20), shuffle: bool}`
   - `match_pairs`: `items: [{left, right}]` (3..12 pairs), `settings: {time_limit_s: 0(off)..600}`
   - `drag_sort`: `categories: [{name}] (2..5)`, `items: [{text, category_index}]` (4..40),
     `settings: {time_limit_s: 0..600}`
   - `word_builder`: `items: [{clue, answer}]` (1..20; answer = letters/digits/spaces, 2..24
     chars, regex `^[A-Za-z0-9 ]{2,24}$`), `settings: {hints_allowed: 0..3}`
   - `sequence`: `items: [{text}]` in correct order (3..10),
     `settings: {time_limit_s: 0..600, shuffle: true always}`
   - Every string ≤500 chars (prompt/clue/left/right/text/name), options ≤200 chars each; whole
     `config` JSON ≤64KB serialized; `answer_index`/`category_index` must be in range; reject
     unknown top-level keys (and unknown keys at every nesting level — `extra="forbid"`
     throughout). All limits re-validated on every update and at publish.
2. **Derived max_score rule:** `max_score` is always derived **server-side as
   `10 × item count`** (`len(config["items"])` for every template — never categories). The
   client mirrors this only for display; the server value wins on results.
3. **award() contract:** `award()` is flush-only; the **caller owns the transaction**; SAVEPOINT
   (`db.begin_nested()`) duplicate-key isolation; every call site wraps in best-effort
   `try/except` — an XP hiccup must never fail the results POST. Event keys, verbatim:
   `game:{game_id}:completed:user:{user_id}` (+20 XP, first completion with score>0) and
   `game:{game_id}:perfect:user:{user_id}` (+10 XP, first `score == max_score`).
4. **Advisory scores, never gradebook:** the `/play` payload includes answers; game results NEVER
   enter the gradebook; the assessment engine remains the graded path (matches the H5P
   advisory-score decision).
5. **noSlashEndpoints:** backend runs `redirect_slashes=False`; `'/games'` MUST be added to
   `noSlashEndpoints` in `frontend/src/api/axios.ts` (the gamification-404 lesson). Every games
   route is declared WITHOUT a trailing slash (create is `@router.post("")`).
6. **Atomic pair rule for game_id:** `lesson_content_type='game'` requires `game_id`; game must
   exist, be `published`, and be owned by the caller (admin any). Flipping content type clears
   the other FK (video → both cleared; h5p → game_id cleared; game → h5p_content_id cleared) —
   "pair or 400", mirroring the H5P helper. Frontend never PATCHes `lesson_content_type='game'`
   without `game_id` in the same request.
7. **XSS posture:** instructor config JSON is untrusted input rendered to other users' browsers.
   **No `dangerouslySetInnerHTML` anywhere in games code**; all item strings render as text via
   React's default escaping only.
8. **Migration guards:** revision `0004_learning_games` (down_revision `0003`) guards every op
   with `has_table`/`_has_column` inspection; SQLite FK column adds/drops use
   `op.batch_alter_table`; downgrade drops in reverse order. Dual-path tolerant with
   `init_db()` create_all, like 0002/0003.
9. **Baseline stays green:** backend `./.venv/Scripts/python -m pytest tests/ -v` (from the
   worktree's `backend/`, shared venv
   `C:\Users\Admin\Downloads\Sasha_lms-main (2)\Sasha_lms-main\backend\.venv\Scripts\python.exe`)
   — zero NEW failures vs the pre-task run. Frontend: `npx vitest run` green;
   `npm run type-check` zero new errors.

**Test commands used throughout:**
- Backend (from `backend/`): `./.venv/Scripts/python -m pytest tests/test_games.py -v`
  (full suite: `./.venv/Scripts/python -m pytest tests/ -v`)
- Frontend (from `frontend/`): `npx vitest run <path>`

**Resolved spec ambiguities (documented here, encoded in the tasks):**
- *quiz_rush speed mapping*: points for a correct answer = `4 + 6 × (time_remaining /
  seconds_per_question)`, rounded, so a correct answer is always in [4,10]. Wrong = 0.
- *quiz_rush streak*: the ×1.5 multiplier applies to a question's points once the current
  correct-answer streak reaches 3 (i.e. from the 3rd consecutive correct answer onward);
  the final total is capped at max_score.
- *sequence retry*: −3 is per item — items scored on the accepted retry submit earn 7 instead
  of 10.
- *word_builder floor*: no floor in spec; floor 0 (hints_allowed ≤ 3 makes the practical
  minimum 4).
- *Owner/admin preview result POST*: spec offers "403 or silently skipped" — we return HTTP 200
  `{"preview": true}` and write nothing (the skip option, friendlier for the shared GamePlayer).
- *Badge slug*: spec names it `game_on` — kept verbatim (underscore) even though older catalog
  slugs use hyphens.
- *award() event_type strings* (spec fixes only event_key formats): `"game_completed"` (+20)
  and `"game_perfect"` (+10), added to `DEFAULT_POINTS`.

---

## Task 1: Models + migration 0004 (+ model tests)

**Files:**
- Create: `backend/app/models/game.py`
- Create: `backend/alembic/versions/0004_learning_games.py`
- Modify: `backend/app/models/course.py` (Lesson: add `game_id` column next to `h5p_content_id`)
- Modify: `backend/app/models/__init__.py` (import the new module so `Base.metadata` sees it)
- Test: `backend/tests/test_games.py` (new — this file grows across Tasks 1–6)

**Interfaces:**
- Produces: `app.models.game.Game`, `app.models.game.GameResult`, `Lesson.game_id`
- Consumes: `app.core.database.Base`, existing `users`/`lessons` tables

**Steps:**

- [ ] Write failing model tests at the top of `backend/tests/test_games.py`:

```python
"""Learning Games backend (docs/superpowers/specs/2026-09-03-learning-games-design.md).

Grows across plan Tasks 1-6: models/migration, config validation, CRUD +
ownership, play gate + results, XP hooks, lesson attach.
SQLite in-memory per repo pattern (see conftest.py).
"""
import pytest

from app.models.course import Course, Lesson
from app.models.enrollment import Enrollment
from app.models.game import Game, GameResult
from app.models.user import User


# ----- factories (mirror tests/test_h5p.py's helpers) ------------------------

def _make_approved_instructor(db, make_user, email):
    from app.models.user import InstructorProfile
    instructor = make_user(role="instructor", email=email)
    profile = db.query(InstructorProfile).filter_by(user_id=instructor.id).first()
    if profile:
        profile.is_approved = True
    else:
        db.add(InstructorProfile(user_id=instructor.id, is_approved=True))
    db.commit()
    return instructor


def _make_course(db, instructor, title="Games Course"):
    course = Course(
        post_author=instructor.id,
        post_title=title,
        post_content="content",
        post_excerpt="excerpt",
        post_status="published",
        post_name=title.lower().replace(" ", "-"),
        course_thumbnail="",
        course_price=0,
        course_level="beginner",
        course_category="Meiporul",
        course_language="English",
        course_duration="10",
    )
    db.add(course)
    db.commit()
    db.refresh(course)
    return course


def _enroll(db, user, course, status="enrolled"):
    e = Enrollment(course_id=course.id, user_id=user.id, enrollment_status=status)
    db.add(e)
    db.commit()
    db.refresh(e)
    return e


def _valid_quiz_rush_config(n_items=2):
    return {
        "items": [
            {"prompt": f"Question {i}?", "options": ["A", "B", "C"], "answer_index": 0}
            for i in range(n_items)
        ],
        "settings": {"seconds_per_question": 20, "shuffle": True},
    }


def _make_game(db, owner, template="quiz_rush", status="draft", config=None, title="Demo Game"):
    game = Game(
        owner_id=owner.id,
        title=title,
        template=template,
        config=config if config is not None else _valid_quiz_rush_config(),
        status=status,
    )
    db.add(game)
    db.commit()
    db.refresh(game)
    return game


def _make_game_lesson(db, course, game_id):
    lesson = Lesson(
        post_author=course.post_author,
        post_parent=course.id,
        post_title="Game Lesson",
        post_content="",
        lesson_content_type="game",
        game_id=game_id,
    )
    db.add(lesson)
    db.commit()
    db.refresh(lesson)
    return lesson


# ============================================================================
# Task 1: models + migration columns
# ============================================================================


class TestGameModels:
    def test_game_defaults(self, db, make_user):
        owner = _make_approved_instructor(db, make_user, "gm-owner@example.com")
        game = _make_game(db, owner)
        assert game.status == "draft"
        assert game.template == "quiz_rush"
        assert isinstance(game.config, dict)
        assert game.created_at is not None
        assert game.updated_at is not None

    def test_game_result_multiple_attempts_allowed(self, db, make_user):
        owner = _make_approved_instructor(db, make_user, "gm-owner2@example.com")
        student = make_user(role="student")
        game = _make_game(db, owner, status="published")
        for score in (10, 15):
            db.add(GameResult(game_id=game.id, user_id=student.id,
                              score=score, max_score=20, duration_s=30))
        db.commit()
        rows = db.query(GameResult).filter_by(game_id=game.id, user_id=student.id).all()
        assert len(rows) == 2  # multiple attempts kept; best computed in queries
        assert rows[0].duration_s == 30

    def test_lesson_game_id_column(self, db, make_user):
        owner = _make_approved_instructor(db, make_user, "gm-owner3@example.com")
        course = _make_course(db, owner)
        game = _make_game(db, owner, status="published")
        lesson = _make_game_lesson(db, course, game.id)
        assert lesson.lesson_content_type == "game"
        assert lesson.game_id == game.id


class TestMigration0004:
    def test_upgrade_creates_tables_and_columns(self, tmp_path):
        """Run 0004's upgrade() against a bare SQLite file DB that already has
        the FK-target tables, then assert games/game_results/lessons.game_id
        exist (mirrors tests/test_live_class_migration.py's approach)."""
        import sqlalchemy as sa
        from alembic.migration import MigrationContext
        from alembic.operations import Operations
        import importlib.util

        engine = sa.create_engine(f"sqlite:///{tmp_path / 'mig.db'}")
        with engine.begin() as conn:
            conn.execute(sa.text("CREATE TABLE users (id INTEGER PRIMARY KEY)"))
            conn.execute(sa.text("CREATE TABLE lessons (id INTEGER PRIMARY KEY)"))
        from pathlib import Path
        path = Path(__file__).resolve().parents[1] / "alembic" / "versions" / "0004_learning_games.py"
        spec = importlib.util.spec_from_file_location("mig_0004", path)
        mig = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mig)

        with engine.connect() as conn:
            ctx = MigrationContext.configure(conn)
            with Operations.context(ctx):
                mig.upgrade()
            conn.commit()

        insp = sa.inspect(engine)
        assert insp.has_table("games")
        assert insp.has_table("game_results")
        lesson_cols = {c["name"] for c in insp.get_columns("lessons")}
        assert "game_id" in lesson_cols
        game_cols = {c["name"] for c in insp.get_columns("games")}
        assert {"id", "owner_id", "title", "template", "config", "status",
                "created_at", "updated_at"} <= game_cols
        result_cols = {c["name"] for c in insp.get_columns("game_results")}
        assert {"id", "game_id", "user_id", "score", "max_score", "duration_s",
                "created_at"} <= result_cols
```

- [ ] Run to see fail: `./.venv/Scripts/python -m pytest tests/test_games.py -v`
      (ImportError: `app.models.game` does not exist).
- [ ] Implement `backend/app/models/game.py`:

```python
"""Learning-game models (spec 2026-09-03-learning-games §2).

`Game` is one instructor-authored game: a `template` key (one of the 5
launch templates) + the JSON `config` that drives the client-side engine.
`max_score` is NEVER stored — it is derived server-side as 10 x item count
(app/schemas/game_config.derive_max_score) everywhere it is needed.

`GameResult` records one advisory play attempt. Multiple attempts are kept
(no unique constraint); "best score" is computed in queries. Per the spec's
security model these scores are advisory engagement data (grading happens
client-side for instant feedback), NEVER gradebook truth — identical
posture to app/models/h5p.H5PResult.
"""
from sqlalchemy import JSON, Column, DateTime, ForeignKey, Integer, String
from sqlalchemy.sql import func

from app.core.database import Base


class Game(Base):
    """One instructor-authored learning game (template + config)."""
    __tablename__ = "games"

    id = Column(Integer, primary_key=True, index=True)
    owner_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)

    title = Column(String(200), nullable=False)
    # One of: quiz_rush | match_pairs | drag_sort | word_builder | sequence
    # (validated by app/schemas/game_config.py — enum enforced at the API
    # layer, not as a DB CHECK, matching lesson_content_type's precedent).
    template = Column(String(32), nullable=False)
    config = Column(JSON, nullable=False)

    # draft (owner-only) -> published (attachable + playable). Unpublish is
    # blocked with 409 while any lesson references the game.
    status = Column(String(16), nullable=False, default="draft")

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    def __repr__(self):
        return f"<Game(id={self.id}, template={self.template}, status={self.status})>"


class GameResult(Base):
    """One advisory play attempt. Multiple rows per (game, user) by design."""
    __tablename__ = "game_results"

    id = Column(Integer, primary_key=True, index=True)
    game_id = Column(Integer, ForeignKey("games.id"), nullable=False, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)

    score = Column(Integer, nullable=False)
    max_score = Column(Integer, nullable=False)
    duration_s = Column(Integer, nullable=False, default=0)

    created_at = Column(DateTime(timezone=True), server_default=func.now())

    def __repr__(self):
        return f"<GameResult(game_id={self.game_id}, user_id={self.user_id}, score={self.score}/{self.max_score})>"
```

- [ ] Add to `backend/app/models/course.py`, directly under the existing
      `h5p_content_id` column on `Lesson`:

```python
    # Learning-game lesson support (spec 2026-09-03-learning-games §2/§3).
    # "game" branches the frontend player to GamePlayer.tsx and requires
    # game_id to point at a published app.models.game.Game row owned by the
    # lesson author (admin any) — validated by courses.py's
    # _resolve_lesson_content_fields, the same atomic-pair helper that
    # guards h5p_content_id.
    game_id = Column(Integer, ForeignKey("games.id"), nullable=True)
```

- [ ] Register the module in `backend/app/models/__init__.py` following its existing import
      style (add `from app.models.game import Game, GameResult  # noqa` — read the file first
      and match exactly how `h5p` is imported there).
- [ ] Implement `backend/alembic/versions/0004_learning_games.py`:

```python
"""learning games — games, game_results, lessons.game_id

Guarded like 0002/0003: init_db()'s create_all may already have created
these tables/columns via the SQLAlchemy models before Alembic runs, so
every operation checks has_table/_has_column first. lessons.game_id uses
batch_alter_table on SQLite (ALTER TABLE ADD COLUMN cannot attach an FK
there — same dance as 0003's lessons.h5p_content_id block, and the FK must
be NAMED in the batch path).

The lesson_content_type allowed-value set grows to ('video','h5p','game')
at the APPLICATION layer only (app/schemas/course.LESSON_CONTENT_TYPES +
courses.py's pair helper) — there is no DB CHECK constraint to alter,
matching how 'h5p' was introduced in 0003.

Revision ID: 0004
Revises: 0003
Create Date: 2026-09-03
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "0004"
down_revision: Union[str, None] = "0003"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _has_column(insp, table_name: str, column_name: str) -> bool:
    if not insp.has_table(table_name):
        return False
    return any(col["name"] == column_name for col in insp.get_columns(table_name))


def upgrade() -> None:
    bind = op.get_bind()
    insp = sa.inspect(bind)

    # ---- games (new table) ----
    if not insp.has_table("games"):
        op.create_table(
            "games",
            sa.Column("id", sa.Integer(), primary_key=True, index=True),
            sa.Column("owner_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
            sa.Column("title", sa.String(200), nullable=False),
            sa.Column("template", sa.String(32), nullable=False),
            sa.Column("config", sa.JSON(), nullable=False),
            sa.Column("status", sa.String(16), nullable=False, server_default="draft"),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
            sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        )
        op.create_index("ix_games_owner_id", "games", ["owner_id"])
    else:
        print("[0004_learning_games] games already exists — skipping create.")

    # ---- game_results (new table) ----
    insp = sa.inspect(bind)  # re-inspect so has_table sees games just created
    if not insp.has_table("game_results") and insp.has_table("games"):
        op.create_table(
            "game_results",
            sa.Column("id", sa.Integer(), primary_key=True, index=True),
            sa.Column("game_id", sa.Integer(), sa.ForeignKey("games.id"), nullable=False),
            sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
            sa.Column("score", sa.Integer(), nullable=False),
            sa.Column("max_score", sa.Integer(), nullable=False),
            sa.Column("duration_s", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        )
        op.create_index("ix_game_results_game_id", "game_results", ["game_id"])
        op.create_index("ix_game_results_user_id", "game_results", ["user_id"])
    elif insp.has_table("game_results"):
        print("[0004_learning_games] game_results already exists — skipping create.")
    else:
        print("[0004_learning_games] games missing — skipping game_results create (FK dependency).")

    # ---- lessons.game_id ----
    insp = sa.inspect(bind)
    if insp.has_table("lessons"):
        if not _has_column(insp, "lessons", "game_id"):
            if insp.has_table("games"):
                if bind.dialect.name == "sqlite":
                    # SQLite can't ADD COLUMN with an FK — batch mode does the
                    # copy-and-move dance; the FK must be NAMED in this path
                    # (mirrors 0003's lessons.h5p_content_id block exactly).
                    with op.batch_alter_table("lessons") as batch_op:
                        batch_op.add_column(sa.Column("game_id", sa.Integer(), nullable=True))
                        batch_op.create_foreign_key(
                            "fk_lessons_game_id", "games", ["game_id"], ["id"]
                        )
                else:
                    op.add_column(
                        "lessons",
                        sa.Column("game_id", sa.Integer(), sa.ForeignKey("games.id"), nullable=True),
                    )
            else:
                print("[0004_learning_games] games missing — skipping lessons.game_id add (FK dependency).")
    else:
        print("[0004_learning_games] lessons table missing entirely — skipping game_id add.")


def downgrade() -> None:
    bind = op.get_bind()
    insp = sa.inspect(bind)

    # Reverse order: drop the FK column first, then the tables it references.
    if insp.has_table("lessons") and _has_column(insp, "lessons", "game_id"):
        if bind.dialect.name == "sqlite":
            with op.batch_alter_table("lessons") as batch_op:
                batch_op.drop_column("game_id")
        else:
            op.drop_column("lessons", "game_id")

    insp = sa.inspect(bind)
    if insp.has_table("game_results"):
        op.drop_table("game_results")

    if insp.has_table("games"):
        op.drop_table("games")
```

- [ ] Run to pass: `./.venv/Scripts/python -m pytest tests/test_games.py -v`
- [ ] Run full backend suite; zero new failures: `./.venv/Scripts/python -m pytest tests/ -v`
- [ ] Commit: `feat(games): Game/GameResult models, lessons.game_id, migration 0004`

---

## Task 2: Per-template config validation schemas + validation tests

**Files:**
- Create: `backend/app/schemas/game_config.py`
- Test: `backend/tests/test_games.py` (append `TestConfigValidation`)

**Interfaces:**
- Produces:
  - `GAME_TEMPLATES: set[str]` = `{"quiz_rush","match_pairs","drag_sort","word_builder","sequence"}`
  - `MAX_CONFIG_BYTES: int` = `64 * 1024`
  - `validate_game_config(template: str, config: dict) -> dict` (returns the normalized config
    dict; raises `GameConfigError(detail: str)` on any violation)
  - `derive_max_score(template: str, config: dict) -> int` (= `10 * len(config["items"])`)
- Consumes: pydantic v1 (`validator`, `Field` — matches `app/schemas/course.py` style)

**Steps:**

- [ ] Append failing tests to `backend/tests/test_games.py`:

```python
# ============================================================================
# Task 2: per-template config validation
# ============================================================================

from app.schemas.game_config import (  # noqa: E402
    GAME_TEMPLATES,
    MAX_CONFIG_BYTES,
    GameConfigError,
    derive_max_score,
    validate_game_config,
)


def _valid_match_pairs_config():
    return {"items": [{"left": f"L{i}", "right": f"R{i}"} for i in range(3)],
            "settings": {"time_limit_s": 0}}


def _valid_drag_sort_config():
    return {"categories": [{"name": "Fruit"}, {"name": "Veg"}],
            "items": [{"text": f"item{i}", "category_index": i % 2} for i in range(4)],
            "settings": {"time_limit_s": 120}}


def _valid_word_builder_config():
    return {"items": [{"clue": "Opposite of down", "answer": "up now"}],
            "settings": {"hints_allowed": 2}}


def _valid_sequence_config():
    return {"items": [{"text": f"Step {i}"} for i in range(3)],
            "settings": {"time_limit_s": 0, "shuffle": True}}


VALID_CONFIGS = {
    "quiz_rush": _valid_quiz_rush_config(),
    "match_pairs": _valid_match_pairs_config(),
    "drag_sort": _valid_drag_sort_config(),
    "word_builder": _valid_word_builder_config(),
    "sequence": _valid_sequence_config(),
}


class TestConfigValidation:
    def test_all_templates_accept_valid_configs(self):
        for template, config in VALID_CONFIGS.items():
            normalized = validate_game_config(template, config)
            assert isinstance(normalized, dict)
            assert "items" in normalized

    def test_unknown_template_rejected(self):
        with pytest.raises(GameConfigError):
            validate_game_config("tetris", {"items": []})
        assert GAME_TEMPLATES == {"quiz_rush", "match_pairs", "drag_sort",
                                  "word_builder", "sequence"}

    def test_unknown_top_level_key_rejected(self):
        cfg = _valid_quiz_rush_config()
        cfg["evil"] = 1
        with pytest.raises(GameConfigError):
            validate_game_config("quiz_rush", cfg)

    def test_unknown_nested_key_rejected(self):
        cfg = _valid_quiz_rush_config()
        cfg["items"][0]["extra"] = "x"
        with pytest.raises(GameConfigError):
            validate_game_config("quiz_rush", cfg)

    def test_oversize_config_rejected(self):
        cfg = _valid_quiz_rush_config(n_items=50)
        # Inflate under the item-count cap but past 64KB serialized.
        for item in cfg["items"]:
            item["prompt"] = "P" * 500
            item["options"] = ["O" * 200] * 6
        assert len(cfg["items"]) == 50
        import json
        assert len(json.dumps(cfg).encode()) > MAX_CONFIG_BYTES
        with pytest.raises(GameConfigError):
            validate_game_config("quiz_rush", cfg)

    # --- per-template invalid matrix ---
    @pytest.mark.parametrize("template,mutate", [
        ("quiz_rush", lambda c: c.update(items=[])),                          # <1 item
        ("quiz_rush", lambda c: c["items"].__iadd__(
            [{"prompt": "x", "options": ["a", "b"], "answer_index": 0}] * 50)),  # >50
        ("quiz_rush", lambda c: c["items"][0].update(options=["only-one"])),  # <2 options
        ("quiz_rush", lambda c: c["items"][0].update(options=["a"] * 7)),     # >6 options
        ("quiz_rush", lambda c: c["items"][0].update(answer_index=99)),       # OOR index
        ("quiz_rush", lambda c: c["settings"].update(seconds_per_question=4)),   # <5
        ("quiz_rush", lambda c: c["settings"].update(seconds_per_question=121)), # >120
        ("quiz_rush", lambda c: c["items"][0].update(prompt="p" * 501)),      # str >500
        ("quiz_rush", lambda c: c["items"][0].update(options=["o" * 201, "b"])),  # opt >200
        ("match_pairs", lambda c: c.update(items=c["items"][:2])),            # <3 pairs
        ("match_pairs", lambda c: c.update(
            items=[{"left": "l", "right": "r"}] * 13)),                       # >12 pairs
        ("match_pairs", lambda c: c["settings"].update(time_limit_s=601)),
        ("drag_sort", lambda c: c.update(categories=[{"name": "one"}])),      # <2 cats
        ("drag_sort", lambda c: c.update(categories=[{"name": "c"}] * 6)),    # >5 cats
        ("drag_sort", lambda c: c.update(items=c["items"][:3])),              # <4 items
        ("drag_sort", lambda c: c["items"][0].update(category_index=9)),      # OOR index
        ("word_builder", lambda c: c["items"][0].update(answer="a")),         # <2 chars
        ("word_builder", lambda c: c["items"][0].update(answer="x" * 25)),    # >24 chars
        ("word_builder", lambda c: c["items"][0].update(answer="bad-char!")), # regex
        ("word_builder", lambda c: c["settings"].update(hints_allowed=4)),    # >3
        ("sequence", lambda c: c.update(items=c["items"][:2])),               # <3 items
        ("sequence", lambda c: c.update(items=[{"text": "t"}] * 11)),         # >10 items
        ("sequence", lambda c: c["settings"].update(shuffle=False)),          # always true
    ])
    def test_invalid_configs_rejected(self, template, mutate):
        import copy
        cfg = copy.deepcopy(VALID_CONFIGS[template])
        mutate(cfg)
        with pytest.raises(GameConfigError):
            validate_game_config(template, cfg)

    def test_quiz_rush_default_seconds_per_question(self):
        cfg = _valid_quiz_rush_config()
        del cfg["settings"]["seconds_per_question"]
        normalized = validate_game_config("quiz_rush", cfg)
        assert normalized["settings"]["seconds_per_question"] == 20

    def test_derived_max_score_is_ten_per_item(self):
        assert derive_max_score("quiz_rush", _valid_quiz_rush_config(7)) == 70
        assert derive_max_score("match_pairs", _valid_match_pairs_config()) == 30
        assert derive_max_score("drag_sort", _valid_drag_sort_config()) == 40   # items, NOT categories
        assert derive_max_score("word_builder", _valid_word_builder_config()) == 10
        assert derive_max_score("sequence", _valid_sequence_config()) == 30
```

- [ ] Run to see fail (ImportError), then implement `backend/app/schemas/game_config.py`:

```python
"""Per-template game-config validation (spec §1, BINDING caps).

Instructor config JSON is UNTRUSTED input that other users' browsers will
render — validation here is a security boundary, not a convenience:
strict per-template pydantic schemas, extra="forbid" at every level, a
64KB serialized-size cap, and in-range index checks. Strings are stored
as-is and rendered as TEXT by React's default escaping (never HTML) — see
the frontend games components.

`max_score` is derived, never stored: 10 x item count, uniformly.
"""
import json
import re

from pydantic import BaseModel, Field, ValidationError, validator
from typing import List

GAME_TEMPLATES = {"quiz_rush", "match_pairs", "drag_sort", "word_builder", "sequence"}
MAX_CONFIG_BYTES = 64 * 1024
MAX_ITEM_STRING = 500     # prompt/clue/left/right/text/name
MAX_OPTION_STRING = 200
WORD_BUILDER_ANSWER_RE = re.compile(r"^[A-Za-z0-9 ]{2,24}$")


class GameConfigError(ValueError):
    def __init__(self, detail: str):
        self.detail = detail
        super().__init__(detail)


class _Strict(BaseModel):
    class Config:
        extra = "forbid"


# ---- quiz_rush -------------------------------------------------------------

class QuizRushItem(_Strict):
    prompt: str = Field(..., min_length=1, max_length=MAX_ITEM_STRING)
    options: List[str] = Field(..., min_items=2, max_items=6)
    answer_index: int

    @validator("options", each_item=True)
    def _option_len(cls, v):
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
    shuffle: bool = False


class QuizRushConfig(_Strict):
    items: List[QuizRushItem] = Field(..., min_items=1, max_items=50)
    settings: QuizRushSettings = QuizRushSettings()


# ---- match_pairs -----------------------------------------------------------

class MatchPairsItem(_Strict):
    left: str = Field(..., min_length=1, max_length=MAX_ITEM_STRING)
    right: str = Field(..., min_length=1, max_length=MAX_ITEM_STRING)


class MatchPairsSettings(_Strict):
    time_limit_s: int = Field(0, ge=0, le=600)  # 0 = off


class MatchPairsConfig(_Strict):
    items: List[MatchPairsItem] = Field(..., min_items=3, max_items=12)
    settings: MatchPairsSettings = MatchPairsSettings()


# ---- drag_sort -------------------------------------------------------------

class DragSortCategory(_Strict):
    name: str = Field(..., min_length=1, max_length=MAX_ITEM_STRING)


class DragSortItem(_Strict):
    text: str = Field(..., min_length=1, max_length=MAX_ITEM_STRING)
    category_index: int = Field(..., ge=0)


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

    @validator("answer")
    def _answer_pattern(cls, v):
        if not WORD_BUILDER_ANSWER_RE.match(v):
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


class SequenceSettings(_Strict):
    time_limit_s: int = Field(0, ge=0, le=600)
    shuffle: bool = True

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
    counts ITEMS, never categories."""
    items = config.get("items") if isinstance(config, dict) else None
    if not isinstance(items, list):
        raise GameConfigError("config has no items list")
    return 10 * len(items)
```

- [ ] Run to pass: `./.venv/Scripts/python -m pytest tests/test_games.py -v`
- [ ] Commit: `feat(games): per-template config validation schemas (64KB cap, extra=forbid)`

---

## Task 3: Games CRUD router (instructor endpoints) + ownership tests

**Files:**
- Create: `backend/app/routers/games.py`
- Modify: `backend/app/main.py` (import + `app.include_router(games.router,
  prefix="/api/v1/games", tags=["Games"])` next to the h5p line ~1316)
- Test: `backend/tests/test_games.py` (append `TestGamesCrud`)

**Interfaces:**
- Produces (all under `/api/v1/games`, NO trailing slashes anywhere):
  - `POST ""` — create draft `{title, template, config}` → game dict
  - `GET /mine` — `{"games": [...], "count": n}` rows:
    `{id, title, template, status, item_count, updated_at, attached_lesson_count}`
  - `GET /{game_id}` — full game incl. config — **owner/admin only, always** (even published:
    other instructors can never read configs)
  - `PUT /{game_id}` — update `{title?, config?}` (owner/admin; re-validates; allowed while
    published)
  - `POST /{game_id}/publish` / `POST /{game_id}/unpublish` — publish re-runs full config
    validation; unpublish 409 while attached to any lesson
  - `DELETE /{game_id}` — owner/admin; 409 while attached
  - `GET /{game_id}/results` — owner/admin rollup (Task 4 fills the query; stub the route here)
- Consumes: `AuthService.require_instructor`, `AuthService.get_current_user`,
  `validate_game_config`, `derive_max_score`, `Game`, `GameResult`, `Lesson`

**Steps:**

- [ ] Append failing tests:

```python
# ============================================================================
# Task 3: CRUD + ownership
# ============================================================================


class TestGamesCrud:
    def test_create_and_get_own_game(self, client, db, make_user, auth_headers):
        owner = _make_approved_instructor(db, make_user, "crud-a@example.com")
        headers = auth_headers(owner.user_email)

        r = client.post("/api/v1/games", json={
            "title": "Fractions Rush",
            "template": "quiz_rush",
            "config": _valid_quiz_rush_config(),
        }, headers=headers)
        assert r.status_code == 200, r.text
        body = r.json()
        assert body["status"] == "draft"
        assert body["max_score"] == 20  # derived, 2 items
        game_id = body["id"]

        r2 = client.get(f"/api/v1/games/{game_id}", headers=headers)
        assert r2.status_code == 200
        assert r2.json()["config"]["items"][0]["prompt"] == "Question 0?"

    def test_create_rejects_invalid_config(self, client, db, make_user, auth_headers):
        owner = _make_approved_instructor(db, make_user, "crud-b@example.com")
        headers = auth_headers(owner.user_email)
        bad = _valid_quiz_rush_config()
        bad["items"][0]["answer_index"] = 99
        r = client.post("/api/v1/games", json={
            "title": "Bad", "template": "quiz_rush", "config": bad,
        }, headers=headers)
        assert r.status_code == 400

    def test_student_cannot_create(self, client, db, make_user, auth_headers):
        student = make_user(role="student")
        r = client.post("/api/v1/games", json={
            "title": "Nope", "template": "quiz_rush",
            "config": _valid_quiz_rush_config(),
        }, headers=auth_headers(student.user_email))
        assert r.status_code == 403

    def test_cross_owner_read_update_delete_blocked(self, client, db, make_user, auth_headers):
        a = _make_approved_instructor(db, make_user, "crud-c@example.com")
        b = _make_approved_instructor(db, make_user, "crud-d@example.com")
        game = _make_game(db, a, status="published")  # even published: config is owner/admin only
        headers_b = auth_headers(b.user_email)

        assert client.get(f"/api/v1/games/{game.id}", headers=headers_b).status_code == 403
        assert client.put(f"/api/v1/games/{game.id}", json={"title": "hijack"},
                          headers=headers_b).status_code == 403
        assert client.delete(f"/api/v1/games/{game.id}", headers=headers_b).status_code == 403

    def test_mine_lists_only_own(self, client, db, make_user, auth_headers):
        a = _make_approved_instructor(db, make_user, "crud-e@example.com")
        b = _make_approved_instructor(db, make_user, "crud-f@example.com")
        _make_game(db, a, title="A's game")
        _make_game(db, b, title="B's game")
        r = client.get("/api/v1/games/mine", headers=auth_headers(a.user_email))
        assert r.status_code == 200
        titles = [g["title"] for g in r.json()["games"]]
        assert titles == ["A's game"]
        row = r.json()["games"][0]
        assert set(row) >= {"id", "title", "template", "status", "item_count",
                            "updated_at", "attached_lesson_count"}
        assert row["item_count"] == 2
        assert row["attached_lesson_count"] == 0

    def test_update_revalidates_config(self, client, db, make_user, auth_headers):
        owner = _make_approved_instructor(db, make_user, "crud-g@example.com")
        game = _make_game(db, owner)
        bad = _valid_quiz_rush_config()
        bad["unknown_key"] = True
        r = client.put(f"/api/v1/games/{game.id}", json={"config": bad},
                       headers=auth_headers(owner.user_email))
        assert r.status_code == 400

    def test_publish_unpublish_and_delete_409_rules(self, client, db, make_user, auth_headers):
        owner = _make_approved_instructor(db, make_user, "crud-h@example.com")
        headers = auth_headers(owner.user_email)
        game = _make_game(db, owner)

        r = client.post(f"/api/v1/games/{game.id}/publish", headers=headers)
        assert r.status_code == 200
        assert r.json()["status"] == "published"

        course = _make_course(db, owner)
        _make_game_lesson(db, course, game.id)

        r2 = client.post(f"/api/v1/games/{game.id}/unpublish", headers=headers)
        assert r2.status_code == 409
        assert "detach" in r2.json()["detail"].lower()
        r3 = client.delete(f"/api/v1/games/{game.id}", headers=headers)
        assert r3.status_code == 409

    def test_admin_sees_all_and_can_manage(self, client, db, make_user, auth_headers):
        owner = _make_approved_instructor(db, make_user, "crud-i@example.com")
        admin = make_user(role="admin", email="crud-admin@example.com")
        game = _make_game(db, owner)
        # Admin login needs TOTP; reuse test_h5p's _admin_headers pattern.
        headers = _admin_headers(client, db, admin)
        assert client.get(f"/api/v1/games/{game.id}", headers=headers).status_code == 200
        r = client.get("/api/v1/games/mine", headers=headers)
        assert any(g["id"] == game.id for g in r.json()["games"])
```

  Also copy `_admin_headers` from `tests/test_h5p.py` (lines 156-174) into `test_games.py`
  verbatim (pyotp TOTP enrolment before login).

- [ ] Run to see fail (404s — router missing), then implement `backend/app/routers/games.py`:

```python
"""Learning Games API (spec §3) — mounted at /api/v1/games.

redirect_slashes=False: every path here is declared WITHOUT a trailing
slash (create is @router.post("")), and '/games' is in axios.ts's
noSlashEndpoints — the gamification-404 lesson.

Ownership (spec §3/§7): configs are owner/admin-only ALWAYS — another
instructor can never read a game's config, draft or published. Students
get published games only through /play (Task 4), gated by enrollment in a
course whose lesson references the game.

Response style: plain dicts, no envelopes (matches h5p.py/gradebook.py).
"""
import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.course import Course, Lesson
from app.models.enrollment import Enrollment
from app.models.game import Game, GameResult
from app.models.user import User
from app.schemas.game_config import (
    GAME_TEMPLATES,
    GameConfigError,
    derive_max_score,
    validate_game_config,
)
from app.services.auth_service import AuthService

router = APIRouter()
logger = logging.getLogger(__name__)

MAX_DURATION_S = 86400


class GameCreate(BaseModel):
    title: str = Field(..., min_length=1, max_length=200)
    template: str
    config: dict


class GameUpdate(BaseModel):
    title: Optional[str] = Field(None, min_length=1, max_length=200)
    config: Optional[dict] = None


class GameResultSubmit(BaseModel):
    score: int
    max_score: int
    duration_s: int = 0


def _get_game_or_404(db: Session, game_id: int) -> Game:
    game = db.query(Game).filter(Game.id == game_id).first()
    if not game:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Game not found")
    return game


def _require_owner_or_admin(game: Game, current_user: User) -> None:
    if game.owner_id != current_user.id and current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized for this game",
        )


def _attached_lessons(db: Session, game_id: int):
    return db.query(Lesson).filter(Lesson.game_id == game_id).all()


def _game_dict(game: Game, include_config: bool = True) -> dict:
    d = {
        "id": game.id,
        "owner_id": game.owner_id,
        "title": game.title,
        "template": game.template,
        "status": game.status,
        "item_count": len((game.config or {}).get("items") or []),
        "max_score": derive_max_score(game.template, game.config),
        "created_at": game.created_at,
        "updated_at": game.updated_at,
    }
    if include_config:
        d["config"] = game.config
    return d


@router.post("")
async def create_game(
    payload: GameCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(AuthService.require_instructor),
):
    """Create a draft game. Config fully validated per template."""
    try:
        normalized = validate_game_config(payload.template, payload.config)
    except GameConfigError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=exc.detail)

    game = Game(
        owner_id=current_user.id,
        title=payload.title.strip(),
        template=payload.template,
        config=normalized,
        status="draft",
    )
    db.add(game)
    db.commit()
    db.refresh(game)
    return _game_dict(game)


@router.get("/mine")
async def list_my_games(
    db: Session = Depends(get_db),
    current_user: User = Depends(AuthService.require_instructor),
):
    """Own games (instructor); admin sees all. Summary rows only (no config)."""
    query = db.query(Game)
    if current_user.role != "admin":
        query = query.filter(Game.owner_id == current_user.id)
    games = query.order_by(Game.updated_at.desc()).all()

    # attached_lesson_count in one grouped query instead of N+1.
    counts = dict(
        db.query(Lesson.game_id, func.count(Lesson.id))
        .filter(Lesson.game_id.in_([g.id for g in games]))
        .group_by(Lesson.game_id)
        .all()
    ) if games else {}

    rows = []
    for g in games:
        row = _game_dict(g, include_config=False)
        row["attached_lesson_count"] = counts.get(g.id, 0)
        rows.append(row)
    return {"games": rows, "count": len(rows)}


@router.get("/{game_id}")
async def get_game(
    game_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(AuthService.require_instructor),
):
    """Full game incl. config — owner/admin only, ALWAYS (spec §3: any other
    instructor cannot read configs, draft or published)."""
    game = _get_game_or_404(db, game_id)
    _require_owner_or_admin(game, current_user)
    return _game_dict(game)


@router.put("/{game_id}")
async def update_game(
    game_id: int,
    payload: GameUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(AuthService.require_instructor),
):
    """Update title/config (owner/admin). Re-validates config; allowed while
    published (spec §3)."""
    game = _get_game_or_404(db, game_id)
    _require_owner_or_admin(game, current_user)

    if payload.config is not None:
        try:
            game.config = validate_game_config(game.template, payload.config)
        except GameConfigError as exc:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=exc.detail)
    if payload.title is not None:
        game.title = payload.title.strip()

    db.commit()
    db.refresh(game)
    return _game_dict(game)


@router.post("/{game_id}/publish")
async def publish_game(
    game_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(AuthService.require_instructor),
):
    """Publish re-runs FULL config validation (spec §1: re-validated at publish)."""
    game = _get_game_or_404(db, game_id)
    _require_owner_or_admin(game, current_user)
    try:
        validate_game_config(game.template, game.config)
    except GameConfigError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot publish: {exc.detail}",
        )
    game.status = "published"
    db.commit()
    db.refresh(game)
    return _game_dict(game)


@router.post("/{game_id}/unpublish")
async def unpublish_game(
    game_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(AuthService.require_instructor),
):
    game = _get_game_or_404(db, game_id)
    _require_owner_or_admin(game, current_user)
    attached = _attached_lessons(db, game.id)
    if attached:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                f"Cannot unpublish: {len(attached)} lesson(s) still use this game. "
                "Detach it from those lessons first."
            ),
        )
    game.status = "draft"
    db.commit()
    db.refresh(game)
    return _game_dict(game)


@router.delete("/{game_id}")
async def delete_game(
    game_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(AuthService.require_instructor),
):
    game = _get_game_or_404(db, game_id)
    _require_owner_or_admin(game, current_user)
    attached = _attached_lessons(db, game.id)
    if attached:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                f"Cannot delete: {len(attached)} lesson(s) still use this game. "
                "Detach it from those lessons first."
            ),
        )
    db.query(GameResult).filter(GameResult.game_id == game.id).delete()
    db.delete(game)
    db.commit()
    return {"success": True, "id": game_id}
```

  (The `/play` + results endpoints are Task 4 — this file grows, same pattern as h5p.py.)

- [ ] Register in `backend/app/main.py`: add `from app.routers import games` next to the h5p
      import (~line 45) and
      `app.include_router(games.router, prefix="/api/v1/games", tags=["Games"])` next to the
      h5p include (~line 1316).
- [ ] Run to pass: `./.venv/Scripts/python -m pytest tests/test_games.py -v`
- [ ] Full suite green: `./.venv/Scripts/python -m pytest tests/ -v`
- [ ] Commit: `feat(games): CRUD router with ownership + publish/unpublish/delete 409 rules`

---

## Task 4: Play gate + results endpoint (clamping, derived max, enrollment gate) + tests

**Files:**
- Modify: `backend/app/routers/games.py` (add `/play`, `POST /results`, `GET /results`)
- Test: `backend/tests/test_games.py` (append `TestPlayGate`, `TestResultsEndpoint`)

**Interfaces:**
- Produces:
  - `GET /api/v1/games/{game_id}/play` → `{id, title, template, config, max_score, preview}` —
    published + enrolled-via-lesson, OR owner/admin (preview=true). Draft for non-owner: 404.
  - `POST /api/v1/games/{game_id}/results` body `{score, max_score, duration_s}` →
    `{game_id, user_id, score, max_score, duration_s, best_score, created_at}`; owner/admin →
    `{"preview": true}` with no write. Server recomputes max_score from config; clamps
    `score` to `[0, derived_max]`, `duration_s` to `[0, 86400]`.
  - `GET /api/v1/games/{game_id}/results` (owner/admin) →
    `{game_id, results: [{user_id, user_name, best_score, max_score, attempts, last_played}], count}`
    — display_name only, **no emails** (spec §3).
- Consumes: `Enrollment` active-status filter (mirrors h5p.py's
  `enrollment_status.notin_(["cancelled", "suspended"])`)

**Steps:**

- [ ] Append failing tests:

```python
# ============================================================================
# Task 4: play gate + results
# ============================================================================


def _setup_playable(db, make_user, owner_email, student_email=None):
    """owner + published game + course + game lesson (+ optional enrolled student)."""
    owner = _make_approved_instructor(db, make_user, owner_email)
    game = _make_game(db, owner, status="published")
    course = _make_course(db, owner, title=f"Course {owner_email}")
    lesson = _make_game_lesson(db, course, game.id)
    student = None
    if student_email:
        student = make_user(role="student", email=student_email)
        _enroll(db, student, course)
    return owner, game, course, lesson, student


class TestPlayGate:
    def test_enrolled_student_gets_payload_with_config(self, client, db, make_user, auth_headers):
        _, game, _, _, student = _setup_playable(
            db, make_user, "pg-a@example.com", "pg-stu-a@example.com")
        r = client.get(f"/api/v1/games/{game.id}/play",
                       headers=auth_headers(student.user_email))
        assert r.status_code == 200, r.text
        body = r.json()
        assert body["preview"] is False
        assert body["max_score"] == 20
        # Answers ship to the client (grading is client-side; advisory only).
        assert body["config"]["items"][0]["answer_index"] == 0

    def test_unenrolled_student_403(self, client, db, make_user, auth_headers):
        _, game, _, _, _ = _setup_playable(db, make_user, "pg-b@example.com")
        outsider = make_user(role="student", email="pg-out@example.com")
        r = client.get(f"/api/v1/games/{game.id}/play",
                       headers=auth_headers(outsider.user_email))
        assert r.status_code == 403

    def test_draft_game_404_for_students(self, client, db, make_user, auth_headers):
        owner = _make_approved_instructor(db, make_user, "pg-c@example.com")
        game = _make_game(db, owner, status="draft")
        student = make_user(role="student", email="pg-stu-c@example.com")
        r = client.get(f"/api/v1/games/{game.id}/play",
                       headers=auth_headers(student.user_email))
        assert r.status_code == 404

    def test_owner_preview_ok_even_draft_and_unattached(self, client, db, make_user, auth_headers):
        owner = _make_approved_instructor(db, make_user, "pg-d@example.com")
        game = _make_game(db, owner, status="draft")
        r = client.get(f"/api/v1/games/{game.id}/play",
                       headers=auth_headers(owner.user_email))
        assert r.status_code == 200
        assert r.json()["preview"] is True


class TestResultsEndpoint:
    def test_result_clamped_to_server_derived_max(self, client, db, make_user, auth_headers):
        _, game, _, _, student = _setup_playable(
            db, make_user, "re-a@example.com", "re-stu-a@example.com")
        r = client.post(f"/api/v1/games/{game.id}/results", json={
            "score": 99999, "max_score": 99999, "duration_s": 999999,
        }, headers=auth_headers(student.user_email))
        assert r.status_code == 200, r.text
        body = r.json()
        assert body["max_score"] == 20      # recomputed from config, not trusted
        assert body["score"] == 20          # clamped to [0, derived_max]
        assert body["duration_s"] == 86400  # clamped to [0, 86400]

    def test_negative_values_clamped_to_zero(self, client, db, make_user, auth_headers):
        _, game, _, _, student = _setup_playable(
            db, make_user, "re-b@example.com", "re-stu-b@example.com")
        r = client.post(f"/api/v1/games/{game.id}/results", json={
            "score": -5, "max_score": 20, "duration_s": -1,
        }, headers=auth_headers(student.user_email))
        assert r.status_code == 200
        assert r.json()["score"] == 0
        assert r.json()["duration_s"] == 0

    def test_unenrolled_post_403_draft_404(self, client, db, make_user, auth_headers):
        _, game, _, _, _ = _setup_playable(db, make_user, "re-c@example.com")
        outsider = make_user(role="student", email="re-out@example.com")
        r = client.post(f"/api/v1/games/{game.id}/results",
                        json={"score": 1, "max_score": 20, "duration_s": 5},
                        headers=auth_headers(outsider.user_email))
        assert r.status_code == 403

        owner2 = _make_approved_instructor(db, make_user, "re-d@example.com")
        draft = _make_game(db, owner2, status="draft")
        student2 = make_user(role="student", email="re-stu-d@example.com")
        r2 = client.post(f"/api/v1/games/{draft.id}/results",
                         json={"score": 1, "max_score": 20, "duration_s": 5},
                         headers=auth_headers(student2.user_email))
        assert r2.status_code == 404

    def test_owner_preview_post_skips_write(self, client, db, make_user, auth_headers):
        owner, game, _, _, _ = _setup_playable(db, make_user, "re-e@example.com")
        r = client.post(f"/api/v1/games/{game.id}/results",
                        json={"score": 10, "max_score": 20, "duration_s": 5},
                        headers=auth_headers(owner.user_email))
        assert r.status_code == 200
        assert r.json() == {"preview": True}
        assert db.query(GameResult).filter_by(game_id=game.id).count() == 0

    def test_multiple_attempts_kept_and_best_reported(self, client, db, make_user, auth_headers):
        owner, game, _, _, student = _setup_playable(
            db, make_user, "re-f@example.com", "re-stu-f@example.com")
        headers = auth_headers(student.user_email)
        client.post(f"/api/v1/games/{game.id}/results",
                    json={"score": 8, "max_score": 20, "duration_s": 40}, headers=headers)
        r = client.post(f"/api/v1/games/{game.id}/results",
                        json={"score": 14, "max_score": 20, "duration_s": 30}, headers=headers)
        assert r.json()["best_score"] == 14
        assert db.query(GameResult).filter_by(
            game_id=game.id, user_id=student.id).count() == 2

        # Instructor rollup: best score, attempts, last played; display_name, NO email.
        r2 = client.get(f"/api/v1/games/{game.id}/results",
                        headers=auth_headers(owner.user_email))
        assert r2.status_code == 200
        rows = r2.json()["results"]
        assert len(rows) == 1
        assert rows[0]["best_score"] == 14
        assert rows[0]["attempts"] == 2
        assert "user_name" in rows[0] and "last_played" in rows[0]
        assert "user_email" not in rows[0] and "email" not in rows[0]

    def test_results_rollup_owner_only(self, client, db, make_user, auth_headers):
        _, game, _, _, _ = _setup_playable(db, make_user, "re-g@example.com")
        other = _make_approved_instructor(db, make_user, "re-h@example.com")
        r = client.get(f"/api/v1/games/{game.id}/results",
                       headers=auth_headers(other.user_email))
        assert r.status_code == 403
```

- [ ] Run to see fail, then append to `backend/app/routers/games.py`:

```python
def _course_ids_with_game_lesson(db: Session, game_id: int) -> set:
    return {
        lesson.post_parent
        for lesson in db.query(Lesson).filter(Lesson.game_id == game_id).all()
    }


def _user_enrolled_for_game(db: Session, game: Game, current_user: User) -> bool:
    """Active enrollment in ANY course containing a lesson attached to this
    game (mirrors h5p.py's _course_for_content_access status filter)."""
    course_ids = _course_ids_with_game_lesson(db, game.id)
    if not course_ids:
        return False
    return (
        db.query(Enrollment)
        .filter(
            Enrollment.user_id == current_user.id,
            Enrollment.course_id.in_(course_ids),
            Enrollment.enrollment_status.notin_(["cancelled", "suspended"]),
        )
        .first()
        is not None
    )


def _gate_play(db: Session, game: Game, current_user: User) -> bool:
    """Shared gate for /play and POST /results. Returns is_preview.
    Owner/admin: always allowed (preview). Others: game must be published
    (404 hides drafts entirely) AND the caller enrolled via an attached
    lesson (403 otherwise)."""
    if game.owner_id == current_user.id or current_user.role == "admin":
        return True
    if game.status != "published":
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Game not found")
    if not _user_enrolled_for_game(db, game, current_user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You must be enrolled in a course containing this game to play it",
        )
    return False


@router.get("/{game_id}/play")
async def get_game_play(
    game_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(AuthService.get_current_user),
):
    """Playable payload. Includes answers — grading is client-side for
    instant feedback, so scores are ADVISORY ONLY and never enter the
    gradebook (spec §3; matches the H5P advisory-score decision)."""
    game = _get_game_or_404(db, game_id)
    is_preview = _gate_play(db, game, current_user)
    return {
        "id": game.id,
        "title": game.title,
        "template": game.template,
        "config": game.config,
        "max_score": derive_max_score(game.template, game.config),
        "preview": is_preview,
    }


@router.post("/{game_id}/results")
async def submit_game_result(
    game_id: int,
    payload: GameResultSubmit,
    db: Session = Depends(get_db),
    current_user: User = Depends(AuthService.get_current_user),
):
    """Record one advisory attempt. Server recomputes max_score from config
    and clamps score/duration — the client-reported numbers are never
    trusted. Owner/admin preview writes NOTHING ({"preview": true} skip)."""
    game = _get_game_or_404(db, game_id)
    is_preview = _gate_play(db, game, current_user)
    if is_preview:
        return {"preview": True}

    derived_max = derive_max_score(game.template, game.config)
    score = max(0, min(int(payload.score), derived_max))
    duration_s = max(0, min(int(payload.duration_s), MAX_DURATION_S))

    result = GameResult(
        game_id=game.id,
        user_id=current_user.id,
        score=score,
        max_score=derived_max,
        duration_s=duration_s,
    )
    db.add(result)
    db.commit()
    db.refresh(result)

    # XP hooks land in Task 5, sequenced AFTER this commit (award() is
    # flush-only; this call site owns the transaction).

    best_score = (
        db.query(func.max(GameResult.score))
        .filter(GameResult.game_id == game.id, GameResult.user_id == current_user.id)
        .scalar()
        or 0
    )
    return {
        "game_id": game.id,
        "user_id": current_user.id,
        "score": result.score,
        "max_score": result.max_score,
        "duration_s": result.duration_s,
        "best_score": best_score,
        "created_at": result.created_at,
    }


@router.get("/{game_id}/results")
async def list_game_results(
    game_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(AuthService.require_instructor),
):
    """Owner/admin: per-student best score, attempts, last played.
    display_name ONLY — never emails (spec §3)."""
    game = _get_game_or_404(db, game_id)
    _require_owner_or_admin(game, current_user)

    rollup = (
        db.query(
            GameResult.user_id,
            func.max(GameResult.score).label("best_score"),
            func.max(GameResult.max_score).label("max_score"),
            func.count(GameResult.id).label("attempts"),
            func.max(GameResult.created_at).label("last_played"),
        )
        .filter(GameResult.game_id == game.id)
        .group_by(GameResult.user_id)
        .all()
    )
    user_ids = [row.user_id for row in rollup]
    users_by_id = {
        u.id: u for u in db.query(User).filter(User.id.in_(user_ids)).all()
    } if user_ids else {}

    rows = [{
        "user_id": row.user_id,
        "user_name": users_by_id[row.user_id].display_name if row.user_id in users_by_id else "Unknown",
        "best_score": row.best_score,
        "max_score": row.max_score,
        "attempts": row.attempts,
        "last_played": row.last_played,
    } for row in rollup]
    return {"game_id": game.id, "results": rows, "count": len(rows)}
```

  **Route-order note:** FastAPI matches in registration order; `GET /mine` (Task 3) MUST stay
  declared before `GET /{game_id}` so "mine" is never captured as a game_id (it would 422 —
  declare-order guards against that class of bug regardless).
- [ ] Run to pass; full suite green.
- [ ] Commit: `feat(games): play gate + advisory results with server-derived max and clamping`

---

## Task 5: XP hooks + badge (event keys, idempotency) + tests

**Files:**
- Modify: `backend/app/services/gamification_service.py` (`DEFAULT_POINTS` + `BADGE_CATALOG` +
  `_badge_rule_satisfied`)
- Modify: `backend/app/routers/games.py` (`submit_game_result` — wire the hooks)
- Test: `backend/tests/test_games.py` (append `TestGameXp`)

**Interfaces:**
- Produces: XP events `game_completed` (+20, key `game:{game_id}:completed:user:{user_id}`,
  first completion with score>0) and `game_perfect` (+10, key
  `game:{game_id}:perfect:user:{user_id}`, first `score == max_score`); badge `game_on`
  ("Completed your first learning game", lucide icon `gamepad-2`).
- Consumes: `award(db, user_id, event_type, event_key, course_id=..., meta=...)` — flush-only,
  caller commits; best-effort try/except at the call site.

**Steps:**

- [ ] Append failing tests:

```python
# ============================================================================
# Task 5: XP hooks + badge
# ============================================================================

from app.models.gamification import Badge, UserBadge, XpEvent  # noqa: E402


class TestGameXp:
    def _post_result(self, client, headers, game_id, score, max_score=20):
        return client.post(f"/api/v1/games/{game_id}/results",
                           json={"score": score, "max_score": max_score, "duration_s": 30},
                           headers=headers)

    def test_first_completion_awards_20_xp_once(self, client, db, make_user, auth_headers):
        _, game, _, _, student = _setup_playable(
            db, make_user, "xp-a@example.com", "xp-stu-a@example.com")
        headers = auth_headers(student.user_email)

        assert self._post_result(client, headers, game.id, 10).status_code == 200
        assert self._post_result(client, headers, game.id, 12).status_code == 200

        events = db.query(XpEvent).filter(
            XpEvent.event_key == f"game:{game.id}:completed:user:{student.id}").all()
        assert len(events) == 1  # idempotent: two completions -> one event
        assert events[0].points == 20

    def test_zero_score_completion_awards_nothing(self, client, db, make_user, auth_headers):
        _, game, _, _, student = _setup_playable(
            db, make_user, "xp-b@example.com", "xp-stu-b@example.com")
        self._post_result(client, auth_headers(student.user_email), game.id, 0)
        assert db.query(XpEvent).filter(
            XpEvent.event_key == f"game:{game.id}:completed:user:{student.id}").count() == 0

    def test_perfect_score_bonus_once(self, client, db, make_user, auth_headers):
        _, game, _, _, student = _setup_playable(
            db, make_user, "xp-c@example.com", "xp-stu-c@example.com")
        headers = auth_headers(student.user_email)
        self._post_result(client, headers, game.id, 20)  # perfect (derived max = 20)
        self._post_result(client, headers, game.id, 20)
        perfect = db.query(XpEvent).filter(
            XpEvent.event_key == f"game:{game.id}:perfect:user:{student.id}").all()
        assert len(perfect) == 1
        assert perfect[0].points == 10

    def test_game_on_badge_awarded_on_first_completion(self, client, db, make_user, auth_headers):
        _, game, _, _, student = _setup_playable(
            db, make_user, "xp-d@example.com", "xp-stu-d@example.com")
        self._post_result(client, auth_headers(student.user_email), game.id, 10)
        badge = db.query(Badge).filter(Badge.slug == "game_on").first()
        assert badge is not None
        assert badge.icon == "gamepad-2"
        assert db.query(UserBadge).filter_by(
            user_id=student.id, badge_id=badge.id).first() is not None

    def test_xp_failure_never_fails_results_post(self, client, db, make_user, auth_headers, monkeypatch):
        _, game, _, _, student = _setup_playable(
            db, make_user, "xp-e@example.com", "xp-stu-e@example.com")

        def _boom(*args, **kwargs):
            raise RuntimeError("gamification down")

        # games.py imports award LAZILY inside the handler
        # (`from app.services.gamification_service import award as _award_xp`),
        # so patching the service module's attribute is sufficient.
        monkeypatch.setattr("app.services.gamification_service.award", _boom)
        r = self._post_result(client, auth_headers(student.user_email), game.id, 10)
        assert r.status_code == 200  # result row still recorded
        assert db.query(GameResult).filter_by(game_id=game.id).count() == 1
```

- [ ] Run to see fail, then modify `gamification_service.py`:
  - In `DEFAULT_POINTS`, add (after `"h5p_completed": 10,`):

```python
    "game_completed": 20,             # first completed learning game with score>0 (spec §4)
    "game_perfect": 10,               # first score == max_score on a learning game (spec §4)
```

  - In `BADGE_CATALOG`, append:

```python
    _BadgeDef("game_on", "Game On", "Completed your first learning game.", "gamepad-2", "games_completed", 1),
```

  - In `_badge_rule_satisfied`, add a branch (next to `h5p_completed`):

```python
    if rt == "games_completed":
        count = db.query(func.count(XpEvent.id)).filter(
            XpEvent.user_id == user_id, XpEvent.event_type == "game_completed"
        ).scalar() or 0
        return count >= (rv or 1)
```

  Note: `ensure_badges` short-circuits on `existing_count >= len(BADGE_CATALOG)` — growing the
  catalog to 16 makes existing deployments seed the new row lazily on the next award. No other
  change needed.

- [ ] In `games.py`'s `submit_game_result`, replace the Task 4 placeholder comment with the
      hooks (AFTER `db.commit()` of the result row — the caller owns the transaction; a
      rollback here can only discard the gamification rows):

```python
    # Gamification (spec §4). Sequenced AFTER the result row's own commit so
    # award()'s flush-only contract holds: this commit/rollback covers ONLY
    # the gamification rows. Best-effort — an XP hiccup never fails the POST.
    try:
        from app.services.gamification_service import award as _award_xp

        course_ids = _course_ids_with_game_lesson(db, game.id)
        course_id = next(iter(course_ids)) if course_ids else None

        if score > 0:
            _award_xp(
                db, current_user.id, "game_completed",
                event_key=f"game:{game.id}:completed:user:{current_user.id}",
                course_id=course_id,
                meta={"game_id": game.id, "template": game.template},
            )
        if score == derived_max:
            _award_xp(
                db, current_user.id, "game_perfect",
                event_key=f"game:{game.id}:perfect:user:{current_user.id}",
                course_id=course_id,
                meta={"game_id": game.id, "template": game.template},
            )
        db.commit()
    except Exception as game_err:
        logger.warning("Gamification award failed for game result: %s", game_err)
        try:
            db.rollback()
        except Exception:
            pass
```

- [ ] Run to pass: `./.venv/Scripts/python -m pytest tests/test_games.py -v`; then
      `./.venv/Scripts/python -m pytest tests/test_gamification.py tests/ -v` (badge-catalog
      growth must not break existing gamification tests — if any assert `len(BADGE_CATALOG) == 15`
      or a fixed badge count, update THAT assertion, noting it here).
- [ ] Commit: `feat(games): XP hooks (game_completed/game_perfect) + game_on badge, idempotent`

---

## Task 6: Lesson attach — extend the pair helper for 'game' + tests

**Files:**
- Modify: `backend/app/routers/courses.py` — rename/extend `_resolve_lesson_h5p_fields`
  (~line 1206) → `_resolve_lesson_content_fields`; update BOTH call sites (create_lesson
  ~line 1339, the lesson update handler ~line 1423)
- Modify: `backend/app/schemas/course.py` — `LESSON_CONTENT_TYPES` += `"game"`; add
  `game_id: Optional[int] = None` to `LessonBase`, `LessonUpdate`, `LessonResponse`,
  `LessonInfo`; add `game_title: Optional[str] = None` to `LessonInfo`
- Modify: `backend/app/services/course_service.py` — where `h5p_public_id` is stitched onto
  lesson payloads (~lines 149-178), also emit `game_id` + `game_title` (single
  `Game.id/Game.title` query over the course's `game_id`s, mirroring the H5P prefetch)
- Test: `backend/tests/test_games.py` (append `TestLessonAttach`)

**Interfaces:**
- Produces:

```python
def _resolve_lesson_content_fields(
    db: Session,
    current_user: User,
    *,
    requested_content_type: Optional[str],
    requested_h5p_content_id: Optional[int],
    requested_game_id: Optional[int],
    existing_content_type: str,
    existing_h5p_content_id: Optional[int],
    existing_game_id: Optional[int],
) -> tuple:  # (content_type, h5p_content_id, game_id)
```

- Rules (BINDING, spec §3 "Lesson attach"): `'game'` requires a resolvable `game_id`; the game
  must exist (404), be `published` (400), and be owned by the caller (403; admin any). Type
  `'video'` clears BOTH FKs; `'h5p'` clears `game_id`; `'game'` clears `h5p_content_id`.

**Steps:**

- [ ] Append failing tests:

```python
# ============================================================================
# Task 6: lesson attach pair rules for 'game'
# ============================================================================


class TestLessonAttach:
    def _create_lesson(self, client, headers, course_id, extra):
        payload = {"title": "Lesson", "content": ""}
        payload.update(extra)
        return client.post(f"/api/v1/courses/{course_id}/lessons", json=payload, headers=headers)

    def test_game_lesson_requires_game_id(self, client, db, make_user, auth_headers):
        owner = _make_approved_instructor(db, make_user, "la-a@example.com")
        course = _make_course(db, owner)
        r = self._create_lesson(client, auth_headers(owner.user_email), course.id,
                                {"lesson_content_type": "game"})
        assert r.status_code == 400
        assert "game_id" in r.json()["detail"]

    def test_game_must_be_published(self, client, db, make_user, auth_headers):
        owner = _make_approved_instructor(db, make_user, "la-b@example.com")
        course = _make_course(db, owner)
        draft = _make_game(db, owner, status="draft")
        r = self._create_lesson(client, auth_headers(owner.user_email), course.id,
                                {"lesson_content_type": "game", "game_id": draft.id})
        assert r.status_code == 400

    def test_cross_owner_game_attach_blocked(self, client, db, make_user, auth_headers):
        a = _make_approved_instructor(db, make_user, "la-c@example.com")
        b = _make_approved_instructor(db, make_user, "la-d@example.com")
        course_b = _make_course(db, b)
        game_a = _make_game(db, a, status="published")
        r = self._create_lesson(client, auth_headers(b.user_email), course_b.id,
                                {"lesson_content_type": "game", "game_id": game_a.id})
        assert r.status_code == 403

    def test_missing_game_404(self, client, db, make_user, auth_headers):
        owner = _make_approved_instructor(db, make_user, "la-e@example.com")
        course = _make_course(db, owner)
        r = self._create_lesson(client, auth_headers(owner.user_email), course.id,
                                {"lesson_content_type": "game", "game_id": 999999})
        assert r.status_code == 404

    def test_valid_attach_and_flip_back_to_video_clears_fk(self, client, db, make_user, auth_headers):
        owner = _make_approved_instructor(db, make_user, "la-f@example.com")
        headers = auth_headers(owner.user_email)
        course = _make_course(db, owner)
        game = _make_game(db, owner, status="published")

        r = self._create_lesson(client, headers, course.id,
                                {"lesson_content_type": "game", "game_id": game.id})
        assert r.status_code == 200, r.text
        lesson_id = r.json()["id"]
        lesson = db.query(Lesson).filter(Lesson.id == lesson_id).first()
        assert lesson.lesson_content_type == "game" and lesson.game_id == game.id

        r2 = client.patch(f"/api/v1/courses/{course.id}/lessons/{lesson_id}",
                          json={"lesson_content_type": "video"}, headers=headers)
        assert r2.status_code == 200, r2.text
        db.refresh(lesson)
        assert lesson.lesson_content_type == "video"
        assert lesson.game_id is None and lesson.h5p_content_id is None

    def test_flip_between_h5p_and_game_clears_other_fk(self, client, db, make_user, auth_headers):
        from app.models.h5p import H5PContent
        from app.services.h5p_service import generate_public_id
        owner = _make_approved_instructor(db, make_user, "la-g@example.com")
        headers = auth_headers(owner.user_email)
        course = _make_course(db, owner)
        game = _make_game(db, owner, status="published")
        content = H5PContent(public_id=generate_public_id(), owner_id=owner.id,
                             title="H5P", library="X 1.0", size_bytes=1, status="ready")
        db.add(content)
        db.commit()
        db.refresh(content)

        r = self._create_lesson(client, headers, course.id,
                                {"lesson_content_type": "h5p", "h5p_content_id": content.id})
        lesson_id = r.json()["id"]

        r2 = client.patch(f"/api/v1/courses/{course.id}/lessons/{lesson_id}",
                          json={"lesson_content_type": "game", "game_id": game.id},
                          headers=headers)
        assert r2.status_code == 200, r2.text
        lesson = db.query(Lesson).filter(Lesson.id == lesson_id).first()
        assert lesson.game_id == game.id and lesson.h5p_content_id is None
```

- [ ] Run to see fail (422 from the schema validator — `"game"` not in `LESSON_CONTENT_TYPES`).
- [ ] Schemas: in `backend/app/schemas/course.py` change line 192 to
      `LESSON_CONTENT_TYPES = {"video", "h5p", "game"}` and add `game_id: Optional[int] = None`
      to `LessonBase` (after `h5p_content_id`), `LessonUpdate`, `LessonResponse`, and
      `LessonInfo` (plus `game_title: Optional[str] = None` on `LessonInfo`).
- [ ] Extend the helper in `backend/app/routers/courses.py` (full replacement of
      `_resolve_lesson_h5p_fields`; add `from app.models.game import Game` to the imports):

```python
def _resolve_lesson_content_fields(
    db: Session,
    current_user: User,
    *,
    requested_content_type: Optional[str],
    requested_h5p_content_id: Optional[int],
    requested_game_id: Optional[int],
    existing_content_type: str,
    existing_h5p_content_id: Optional[int],
    existing_game_id: Optional[int],
) -> tuple:
    """Validate + resolve the (lesson_content_type, h5p_content_id, game_id)
    triple for a lesson create/update — single source of truth for the
    atomic-pair contract ('pair or 400'). Extends the former
    _resolve_lesson_h5p_fields for 'game' (spec 2026-09-03 §3):

      - 'video'  -> clears BOTH FKs.
      - 'h5p'    -> requires a ready, caller-owned H5PContent; clears game_id.
      - 'game'   -> requires a PUBLISHED, caller-owned Game (admin any);
                    clears h5p_content_id. 404 unknown id, 400 unpublished,
                    403 cross-owner.
    """
    effective_type = requested_content_type if requested_content_type is not None else existing_content_type
    if effective_type not in ("video", "h5p", "game"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="lesson_content_type must be one of ['game', 'h5p', 'video']",
        )

    if effective_type == "video":
        return "video", None, None

    if effective_type == "h5p":
        effective_h5p_id = (
            requested_h5p_content_id if requested_h5p_content_id is not None else existing_h5p_content_id
        )
        if effective_h5p_id is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="h5p_content_id is required when lesson_content_type is 'h5p'",
            )
        content = db.query(H5PContent).filter(H5PContent.id == effective_h5p_id).first()
        if not content:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="H5P content not found")
        if content.status != "ready":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"H5P content is not ready (status={content.status})",
            )
        if content.owner_id != current_user.id and current_user.role != "admin":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You can only attach your own H5P content to a lesson",
            )
        return "h5p", effective_h5p_id, None

    # effective_type == "game"
    effective_game_id = requested_game_id if requested_game_id is not None else existing_game_id
    if effective_game_id is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="game_id is required when lesson_content_type is 'game'",
        )
    game = db.query(Game).filter(Game.id == effective_game_id).first()
    if not game:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Game not found")
    if game.status != "published":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Game must be published before it can be attached to a lesson",
        )
    if game.owner_id != current_user.id and current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only attach your own games to a lesson",
        )
    return "game", None, effective_game_id
```

- [ ] Update BOTH call sites. `create_lesson` (~line 1339):

```python
    resolved_content_type, resolved_h5p_content_id, resolved_game_id = _resolve_lesson_content_fields(
        db,
        current_user,
        requested_content_type=lesson_data.lesson_content_type,
        requested_h5p_content_id=lesson_data.h5p_content_id,
        requested_game_id=lesson_data.game_id,
        existing_content_type="video",
        existing_h5p_content_id=None,
        existing_game_id=None,
    )
```

  and pass `game_id=resolved_game_id` where the `Lesson(...)` is constructed (next to
  `h5p_content_id=resolved_h5p_content_id` — find where the create handler assigns those and
  mirror). Lesson update handler (~line 1423):

```python
    if (
        lesson_data.lesson_content_type is not None
        or lesson_data.h5p_content_id is not None
        or lesson_data.game_id is not None
    ):
        resolved_content_type, resolved_h5p_content_id, resolved_game_id = _resolve_lesson_content_fields(
            db,
            current_user,
            requested_content_type=lesson_data.lesson_content_type,
            requested_h5p_content_id=lesson_data.h5p_content_id,
            requested_game_id=lesson_data.game_id,
            existing_content_type=lesson.lesson_content_type or "video",
            existing_h5p_content_id=lesson.h5p_content_id,
            existing_game_id=lesson.game_id,
        )
        lesson.lesson_content_type = resolved_content_type
        lesson.h5p_content_id = resolved_h5p_content_id
        lesson.game_id = resolved_game_id
```

- [ ] `course_service.py`: next to the `h5p_public_id_by_content_id` prefetch (~line 149) add:

```python
        game_ids = {
            lesson.game_id for lesson in course.lessons if getattr(lesson, "game_id", None)
        }
        game_title_by_id: Dict[int, str] = {}
        if game_ids and db:
            from app.models.game import Game
            rows = db.query(Game.id, Game.title).filter(Game.id.in_(game_ids)).all()
            game_title_by_id = {row.id: row.title for row in rows}
```

  and in both loops that append `lesson_data` (~lines 172, 178):

```python
                lesson_data["game_id"] = lesson.game_id
                lesson_data["game_title"] = game_title_by_id.get(lesson.game_id)
```

- [ ] Run to pass: `./.venv/Scripts/python -m pytest tests/test_games.py tests/test_h5p.py -v`
      (the h5p suite exercises the same helper — it must stay green through the rename).
- [ ] Full suite green.
- [ ] Commit: `feat(games): lesson attach — content-type triple helper (video|h5p|game), atomic pair`

---

## Task 7: Frontend api/games.ts + pure engine scoring functions + '/games' noSlash

**Files:**
- Create: `frontend/src/api/games.ts`
- Create: `frontend/src/components/games/engines/scoring.ts`
- Modify: `frontend/src/api/axios.ts` (noSlashEndpoints)
- Test: `frontend/src/components/games/engines/__tests__/scoring.test.ts`

**Interfaces:**
- Produces (consumed verbatim by Tasks 8–11): all types/functions below.
- Consumes: `api` from `@/api/axios`; backend shapes from Tasks 3–4.

**Steps:**

- [ ] In `frontend/src/api/axios.ts`, append to `noSlashEndpoints` (after the `'/live'` entry):

```typescript
        // Learning Games endpoints (spec §3). redirect_slashes=False and no
        // games route declares a trailing slash — /games, /games/mine,
        // /games/{id}, /games/{id}/play, /games/{id}/results,
        // /games/{id}/publish, /games/{id}/unpublish all 404 with one appended.
        '/games'
```

- [ ] Write failing scoring tests
      (`frontend/src/components/games/engines/__tests__/scoring.test.ts`):

```typescript
import { describe, expect, it } from 'vitest'
import {
  capScore,
  deriveMaxScore,
  scoreDragSortItem,
  scoreMatchPair,
  scoreQuizRushAnswer,
  scoreSequenceSubmit,
  scoreWordBuilderItem,
  QUIZ_RUSH_STREAK_THRESHOLD,
} from '../scoring'

describe('deriveMaxScore', () => {
  it('is 10 x item count (mirrors the server rule)', () => {
    expect(deriveMaxScore(0)).toBe(0)
    expect(deriveMaxScore(7)).toBe(70)
  })
})

describe('scoreQuizRushAnswer', () => {
  it('wrong answer is 0 regardless of time', () => {
    expect(scoreQuizRushAnswer(false, 20, 20, 5)).toBe(0)
  })
  it('instant correct answer earns 10, last-moment earns floor 4', () => {
    expect(scoreQuizRushAnswer(true, 20, 20, 0)).toBe(10)
    expect(scoreQuizRushAnswer(true, 0, 20, 0)).toBe(4)
  })
  it('halfway remaining earns 7 (linear 4 + 6 x fraction, rounded)', () => {
    expect(scoreQuizRushAnswer(true, 10, 20, 0)).toBe(7)
  })
  it('streak >= threshold multiplies the answer points by 1.5', () => {
    expect(QUIZ_RUSH_STREAK_THRESHOLD).toBe(3)
    expect(scoreQuizRushAnswer(true, 20, 20, 3)).toBe(15) // 10 * 1.5
    expect(scoreQuizRushAnswer(true, 20, 20, 2)).toBe(10) // below threshold
  })
})

describe('capScore', () => {
  it('caps the running total at max_score', () => {
    expect(capScore(37, 30)).toBe(30)
    expect(capScore(12, 30)).toBe(12)
    expect(capScore(-1, 30)).toBe(0)
  })
})

describe('scoreMatchPair', () => {
  it('10 per pair minus 1 per extra miss, floor 3', () => {
    expect(scoreMatchPair(0)).toBe(10)
    expect(scoreMatchPair(2)).toBe(8)
    expect(scoreMatchPair(15)).toBe(3)
  })
})

describe('scoreDragSortItem', () => {
  it('10 per correct placement, -3 per bounce-back retry, floor 2', () => {
    expect(scoreDragSortItem(0)).toBe(10)
    expect(scoreDragSortItem(1)).toBe(7)
    expect(scoreDragSortItem(2)).toBe(4)
    expect(scoreDragSortItem(3)).toBe(2)
    expect(scoreDragSortItem(9)).toBe(2)
  })
})

describe('scoreWordBuilderItem', () => {
  it('10 minus 2 per hint used, floor 0', () => {
    expect(scoreWordBuilderItem(0)).toBe(10)
    expect(scoreWordBuilderItem(3)).toBe(4)
    expect(scoreWordBuilderItem(6)).toBe(0)
  })
})

describe('scoreSequenceSubmit', () => {
  it('10 per correct final position on first submit, 7 on the retry', () => {
    expect(scoreSequenceSubmit(4, false)).toBe(40)
    expect(scoreSequenceSubmit(4, true)).toBe(28)
    expect(scoreSequenceSubmit(0, true)).toBe(0)
  })
})
```

- [ ] Run to see fail: `npx vitest run src/components/games/engines/__tests__/scoring.test.ts`
- [ ] Implement `frontend/src/components/games/engines/scoring.ts`:

```typescript
/**
 * Deterministic scoring functions for the 5 game templates (spec §1's
 * table, BINDING). Pure and unit-tested; the engine components call these
 * and never inline score math. The server clamps whatever we report to
 * its own derived max, so these functions are UX truth, not security.
 */

/** Uniform rule: max_score = 10 x item count (server derives the same). */
export function deriveMaxScore(itemCount: number): number {
  return itemCount * 10
}

/** Clamp a running total into [0, maxScore] (quiz_rush streak cap etc.). */
export function capScore(total: number, maxScore: number): number {
  return Math.max(0, Math.min(total, maxScore))
}

/** Streak length at which the x1.5 multiplier kicks in (resolved ambiguity:
 * from the 3rd consecutive correct answer onward). */
export const QUIZ_RUSH_STREAK_THRESHOLD = 3

/**
 * quiz_rush: faster answer = more of the 10 pts. Linear 4 + 6 x
 * (timeRemaining / secondsPerQuestion), rounded — floor 4 on correct,
 * 0 on wrong. `streakBefore` = consecutive correct answers BEFORE this
 * one; at >= threshold the answer's points are multiplied by 1.5
 * (total capped at max_score by the caller via capScore).
 */
export function scoreQuizRushAnswer(
  correct: boolean,
  timeRemainingS: number,
  secondsPerQuestion: number,
  streakBefore: number
): number {
  if (!correct) return 0
  const fraction = secondsPerQuestion > 0
    ? Math.max(0, Math.min(1, timeRemainingS / secondsPerQuestion))
    : 0
  let points = Math.round(4 + 6 * fraction)
  if (streakBefore >= QUIZ_RUSH_STREAK_THRESHOLD) {
    points = Math.round(points * 1.5)
  }
  return points
}

/** match_pairs: 10 pts per pair minus 1 per extra miss on that pair, floor 3. */
export function scoreMatchPair(misses: number): number {
  return Math.max(3, 10 - misses)
}

/** drag_sort: 10 pts per correctly placed item; each wrong placement
 * bounces back at -3, floor 2. `wrongAttempts` = bounce-backs before the
 * correct placement. */
export function scoreDragSortItem(wrongAttempts: number): number {
  return Math.max(2, 10 - 3 * wrongAttempts)
}

/** word_builder: 10 pts, -2 per hint used (hints_allowed <= 3), floor 0. */
export function scoreWordBuilderItem(hintsUsed: number): number {
  return Math.max(0, 10 - 2 * hintsUsed)
}

/** sequence: 10 pts per item in correct final position on the accepted
 * submit — 7 per item when that submit is the one allowed retry (-3). */
export function scoreSequenceSubmit(correctCount: number, isRetry: boolean): number {
  return correctCount * (isRetry ? 7 : 10)
}
```

- [ ] Implement `frontend/src/api/games.ts`:

```typescript
/**
 * Learning Games API client — typed wrapper around /api/v1/games/*
 * (backend/app/routers/games.py). '/games' is in axios.ts's
 * noSlashEndpoints: the backend runs redirect_slashes=False and no games
 * route declares a trailing slash.
 */
import { api } from './axios'

export type GameTemplate =
  | 'quiz_rush'
  | 'match_pairs'
  | 'drag_sort'
  | 'word_builder'
  | 'sequence'

export type GameStatus = 'draft' | 'published'

export interface QuizRushConfig {
  items: { prompt: string; options: string[]; answer_index: number }[]
  settings: { seconds_per_question: number; shuffle: boolean }
}
export interface MatchPairsConfig {
  items: { left: string; right: string }[]
  settings: { time_limit_s: number }
}
export interface DragSortConfig {
  categories: { name: string }[]
  items: { text: string; category_index: number }[]
  settings: { time_limit_s: number }
}
export interface WordBuilderConfig {
  items: { clue: string; answer: string }[]
  settings: { hints_allowed: number }
}
export interface SequenceConfig {
  items: { text: string }[]
  settings: { time_limit_s: number; shuffle: true }
}
export type GameConfig =
  | QuizRushConfig
  | MatchPairsConfig
  | DragSortConfig
  | WordBuilderConfig
  | SequenceConfig

export interface Game {
  id: number
  owner_id: number
  title: string
  template: GameTemplate
  status: GameStatus
  item_count: number
  max_score: number
  config: GameConfig
  created_at: string
  updated_at: string
}

/** GET /games/mine row (no config). */
export interface GameSummary {
  id: number
  owner_id: number
  title: string
  template: GameTemplate
  status: GameStatus
  item_count: number
  max_score: number
  attached_lesson_count: number
  created_at: string
  updated_at: string
}

export interface GamePlayPayload {
  id: number
  title: string
  template: GameTemplate
  config: GameConfig
  max_score: number
  preview: boolean
}

export interface SubmitGameResultPayload {
  score: number
  max_score: number
  duration_s: number
}

export interface GameResultResponse {
  game_id: number
  user_id: number
  score: number
  max_score: number
  duration_s: number
  best_score: number
  created_at: string
}

export interface GameResultRow {
  user_id: number
  user_name: string
  best_score: number
  max_score: number
  attempts: number
  last_played: string
}

export async function listMyGames(): Promise<{ games: GameSummary[]; count: number }> {
  const response = await api.get('/games/mine')
  return response.data
}

export async function getGame(gameId: number): Promise<Game> {
  const response = await api.get<Game>(`/games/${gameId}`)
  return response.data
}

export async function createGame(payload: {
  title: string
  template: GameTemplate
  config: GameConfig
}): Promise<Game> {
  const response = await api.post<Game>('/games', payload)
  return response.data
}

export async function updateGame(
  gameId: number,
  payload: { title?: string; config?: GameConfig }
): Promise<Game> {
  const response = await api.put<Game>(`/games/${gameId}`, payload)
  return response.data
}

export async function publishGame(gameId: number): Promise<Game> {
  const response = await api.post<Game>(`/games/${gameId}/publish`)
  return response.data
}

export async function unpublishGame(gameId: number): Promise<Game> {
  const response = await api.post<Game>(`/games/${gameId}/unpublish`)
  return response.data
}

export async function deleteGame(gameId: number): Promise<{ success: boolean; id: number }> {
  const response = await api.delete(`/games/${gameId}`)
  return response.data
}

export async function getGamePlay(gameId: number): Promise<GamePlayPayload> {
  const response = await api.get<GamePlayPayload>(`/games/${gameId}/play`)
  return response.data
}

/** Owner/admin preview POSTs come back as {preview: true} with nothing written. */
export async function submitGameResult(
  gameId: number,
  payload: SubmitGameResultPayload
): Promise<GameResultResponse | { preview: true }> {
  const response = await api.post(`/games/${gameId}/results`, payload)
  return response.data
}

export async function listGameResults(
  gameId: number
): Promise<{ game_id: number; results: GameResultRow[]; count: number }> {
  const response = await api.get(`/games/${gameId}/results`)
  return response.data
}
```

- [ ] Run to pass: `npx vitest run src/components/games/engines/__tests__/scoring.test.ts`;
      `npm run type-check` (no new errors).
- [ ] Commit: `feat(games): typed api client, pure scoring functions, '/games' noSlash entry`

---

## Task 8: GameShell + 5 engine components + GamePlayer

**Files:**
- Create: `frontend/src/components/games/GameShell.tsx`
- Create: `frontend/src/components/games/engines/QuizRush.tsx`, `engines/MatchPairs.tsx`,
  `engines/DragSort.tsx`, `engines/WordBuilder.tsx`, `engines/SequenceGame.tsx`
- Create: `frontend/src/components/games/GamePlayer.tsx`
- Test: `frontend/src/components/games/__tests__/GamePlayer.test.tsx`

**Interfaces:**
- Produces (used verbatim by Tasks 9–11):

```typescript
export interface GameOutcome { score: number; maxScore: number; durationS: number }
export interface EngineProps<C> { config: C; onComplete: (outcome: GameOutcome) => void }
// engines: QuizRush: React.FC<EngineProps<QuizRushConfig>>, MatchPairs:
// React.FC<EngineProps<MatchPairsConfig>>, DragSort, WordBuilder, SequenceGame likewise.

export interface GamePlayerProps {
  gameId: number
  /** Instructor preview: play normally but NEVER POST a result and never
   * fire onLessonComplete — mirrors H5PLesson's previewOnly semantics. */
  previewOnly?: boolean
  /** Fired once, after the result POST resolves successfully, when embedded
   * in a lesson (lesson-redesigned wires its lesson-complete call here). */
  onLessonComplete?: () => void
  className?: string
}
```

- Consumes: `getGamePlay`, `submitGameResult` (Task 7), scoring functions (Task 7),
  `@dnd-kit/core` + `@dnd-kit/sortable` for DragSort/SequenceGame touch-capable drag.

**Steps:**

- [ ] Write failing GamePlayer tests (mirror `H5PPicker.test.tsx`'s mocking conventions —
      read that file for the render/mocking setup used in this repo):

```tsx
import { render, screen, waitFor } from '@testing-library/react'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import * as gamesApi from '@/api/games'
import { GamePlayer } from '../GamePlayer'

vi.mock('@/api/games', async (importOriginal) => {
  const actual = await importOriginal<typeof gamesApi>()
  return {
    ...actual,
    getGamePlay: vi.fn(),
    submitGameResult: vi.fn(),
  }
})

const playPayload: gamesApi.GamePlayPayload = {
  id: 1,
  title: 'Fractions Rush',
  template: 'quiz_rush',
  config: {
    items: [{ prompt: 'Q1?', options: ['a', 'b'], answer_index: 0 }],
    settings: { seconds_per_question: 20, shuffle: false },
  },
  max_score: 10,
  preview: false,
}

describe('GamePlayer', () => {
  beforeEach(() => {
    vi.mocked(gamesApi.getGamePlay).mockResolvedValue(playPayload)
    vi.mocked(gamesApi.submitGameResult).mockResolvedValue({
      game_id: 1, user_id: 2, score: 10, max_score: 10, duration_s: 5,
      best_score: 10, created_at: 'now',
    })
  })

  it('fetches the play payload and renders the game title', async () => {
    render(<GamePlayer gameId={1} />)
    await waitFor(() => expect(screen.getByText('Fractions Rush')).toBeInTheDocument())
    expect(gamesApi.getGamePlay).toHaveBeenCalledWith(1)
  })

  it('POSTs the result and fires onLessonComplete on engine completion', async () => {
    const onLessonComplete = vi.fn()
    render(<GamePlayer gameId={1} onLessonComplete={onLessonComplete} />)
    await waitFor(() => expect(screen.getByText('Fractions Rush')).toBeInTheDocument())
    // Drive completion through the exported test hook (see GamePlayer:
    // engines call handleComplete; the test invokes it via the completion
    // path by finishing the single-question quiz).
    screen.getByRole('button', { name: 'a' }).click()
    await waitFor(() =>
      expect(gamesApi.submitGameResult).toHaveBeenCalledWith(1, {
        score: expect.any(Number), max_score: 10, duration_s: expect.any(Number),
      })
    )
    await waitFor(() => expect(onLessonComplete).toHaveBeenCalledTimes(1))
  })

  it('previewOnly suppresses the result POST and onLessonComplete', async () => {
    const onLessonComplete = vi.fn()
    vi.mocked(gamesApi.getGamePlay).mockResolvedValue({ ...playPayload, preview: true })
    render(<GamePlayer gameId={1} previewOnly onLessonComplete={onLessonComplete} />)
    await waitFor(() => expect(screen.getByText('Fractions Rush')).toBeInTheDocument())
    screen.getByRole('button', { name: 'a' }).click()
    // GameShell's results screen replaces the question with the replay CTA.
    await waitFor(() =>
      expect(screen.getByRole('button', { name: /play again/i })).toBeInTheDocument())
    expect(gamesApi.submitGameResult).not.toHaveBeenCalled()
    expect(onLessonComplete).not.toHaveBeenCalled()
  })
})
```

- [ ] Run to see fail: `npx vitest run src/components/games/__tests__/GamePlayer.test.tsx`
- [ ] Implement `GameShell.tsx` (frame every engine renders inside — title bar, SVG timer ring,
      score counter, progress dots, pause, results screen with replay + CSS/SVG confetti
      respecting `prefers-reduced-motion`):

```tsx
/**
 * GameShell — shared chrome for all 5 engines (spec §6): title bar, SVG
 * timer ring, score counter, progress dots, pause overlay, and the results
 * screen (score, best score, replay, pure CSS/SVG confetti that respects
 * prefers-reduced-motion). All strings render as React text — instructor
 * config is untrusted; NO dangerouslySetInnerHTML anywhere in games code.
 */
import * as React from 'react'
import { Pause, Play, RotateCcw } from 'lucide-react'

export interface GameShellResult {
  score: number
  maxScore: number
  bestScore?: number | null
}

export interface GameShellProps {
  title: string
  accentClass?: string          // per-template Tailwind accent, e.g. 'text-violet-600'
  currentIndex: number          // 0-based progress dot position
  totalItems: number
  score: number
  maxScore: number
  timeRemainingS?: number | null // null = untimed
  totalTimeS?: number | null
  paused: boolean
  onPauseToggle: () => void
  result?: GameShellResult | null // non-null flips to the results screen
  onReplay: () => void
  children: React.ReactNode
}

export const GameShell: React.FC<GameShellProps> = ({
  title, accentClass = 'text-primary-600', currentIndex, totalItems, score,
  maxScore, timeRemainingS, totalTimeS, paused, onPauseToggle, result,
  onReplay, children,
}) => {
  const prefersReducedMotion = React.useMemo(
    () => typeof window !== 'undefined'
      && window.matchMedia?.('(prefers-reduced-motion: reduce)').matches,
    []
  )
  const ringFraction =
    timeRemainingS != null && totalTimeS ? Math.max(0, timeRemainingS / totalTimeS) : null

  if (result) {
    return (
      <div className="flex flex-col items-center justify-center gap-4 p-8 text-center">
        {!prefersReducedMotion && <ConfettiBurst />}
        <h2 className="text-xl font-bold text-gray-900">{title}</h2>
        <p className="text-4xl font-extrabold tabular-nums">
          {result.score} <span className="text-gray-400 text-2xl">/ {result.maxScore}</span>
        </p>
        {result.bestScore != null && (
          <p className="text-sm text-gray-500">Best score: {result.bestScore}</p>
        )}
        <button type="button" onClick={onReplay}
          className="inline-flex items-center gap-2 px-4 py-2 rounded-lg bg-primary-600 text-white text-sm font-medium">
          <RotateCcw className="w-4 h-4" /> Play again
        </button>
      </div>
    )
  }

  return (
    <div className="flex flex-col h-full">
      <div className="flex items-center justify-between gap-3 px-4 py-2 border-b border-gray-100">
        <p className={`font-semibold truncate ${accentClass}`}>{title}</p>
        <div className="flex items-center gap-3 shrink-0">
          {ringFraction != null && (
            <svg viewBox="0 0 36 36" className="w-8 h-8 -rotate-90" aria-label="Time remaining">
              <circle cx="18" cy="18" r="15" fill="none" strokeWidth="3" className="stroke-gray-200" />
              <circle cx="18" cy="18" r="15" fill="none" strokeWidth="3"
                className="stroke-current" strokeDasharray={`${ringFraction * 94.2} 94.2`} />
            </svg>
          )}
          <span className="text-sm font-semibold tabular-nums">{score}/{maxScore}</span>
          <button type="button" onClick={onPauseToggle} aria-label={paused ? 'Resume' : 'Pause'}
            className="text-gray-500 hover:text-gray-800">
            {paused ? <Play className="w-4 h-4" /> : <Pause className="w-4 h-4" />}
          </button>
        </div>
      </div>
      <div className="flex justify-center gap-1.5 py-2" aria-label="Progress">
        {Array.from({ length: totalItems }).map((_, i) => (
          <span key={i} className={`w-2 h-2 rounded-full ${i <= currentIndex ? 'bg-primary-500' : 'bg-gray-200'}`} />
        ))}
      </div>
      <div className="relative flex-1 min-h-0">
        {paused && (
          <div className="absolute inset-0 z-10 bg-white/90 flex items-center justify-center">
            <p className="text-gray-600 font-medium">Paused</p>
          </div>
        )}
        {children}
      </div>
    </div>
  )
}

/** Pure CSS/SVG confetti — ~20 absolutely-positioned falling shapes, no images. */
const ConfettiBurst: React.FC = () => (
  <div aria-hidden className="pointer-events-none fixed inset-0 overflow-hidden">
    {Array.from({ length: 20 }).map((_, i) => (
      <span key={i}
        className="absolute w-2 h-3 rounded-sm animate-[confetti-fall_1.8s_ease-in_forwards]"
        style={{
          left: `${(i * 5) % 100}%`,
          backgroundColor: ['#7c3aed', '#f59e0b', '#10b981', '#ef4444'][i % 4],
          animationDelay: `${(i % 7) * 0.12}s`,
        }} />
    ))}
  </div>
)

export default GameShell
```

  Add the `confetti-fall` keyframes to the games components via a small `<style>` in
  GameShell or Tailwind config-free arbitrary keyframes — implementer's choice, but pure
  CSS/SVG only.

- [ ] Implement the 5 engines as pure-props components. Full skeleton for `QuizRush.tsx`
      (the other four follow the identical shape — state machine + scoring fn + `GameShell`;
      `DragSort`/`SequenceGame` use `@dnd-kit/core`'s `DndContext` + `useDraggable`/
      `useDroppable` and `@dnd-kit/sortable` respectively for touch support):

```tsx
/** QuizRush — timed MCQ race (spec §1 row 1). Pure props; scoring via
 * engines/scoring.ts only. All config strings render as React TEXT. */
import * as React from 'react'
import type { QuizRushConfig } from '@/api/games'
import { GameShell } from '../GameShell'
import {
  capScore,
  deriveMaxScore,
  scoreQuizRushAnswer,
} from './scoring'

export interface GameOutcome {
  score: number
  maxScore: number
  durationS: number
}

export interface EngineProps<C> {
  config: C
  onComplete: (outcome: GameOutcome) => void
  title?: string
}

function shuffled<T>(arr: T[]): T[] {
  const copy = [...arr]
  for (let i = copy.length - 1; i > 0; i--) {
    const j = Math.floor(Math.random() * (i + 1))
    ;[copy[i], copy[j]] = [copy[j], copy[i]]
  }
  return copy
}

export const QuizRush: React.FC<EngineProps<QuizRushConfig>> = ({ config, onComplete, title = '' }) => {
  const items = React.useMemo(
    () => (config.settings.shuffle ? shuffled(config.items) : config.items),
    [config]
  )
  const maxScore = deriveMaxScore(config.items.length)
  const perQuestion = config.settings.seconds_per_question

  const [index, setIndex] = React.useState(0)
  const [score, setScore] = React.useState(0)
  const [streak, setStreak] = React.useState(0)
  const [timeRemaining, setTimeRemaining] = React.useState(perQuestion)
  const [paused, setPaused] = React.useState(false)
  const [done, setDone] = React.useState(false)
  const startedAtRef = React.useRef(Date.now())
  const completedRef = React.useRef(false)

  const finish = React.useCallback((finalScore: number) => {
    if (completedRef.current) return
    completedRef.current = true
    setDone(true)
    onComplete({
      score: capScore(finalScore, maxScore),
      maxScore,
      durationS: Math.round((Date.now() - startedAtRef.current) / 1000),
    })
  }, [maxScore, onComplete])

  const answer = React.useCallback((optionIndex: number | null) => {
    const item = items[index]
    const correct = optionIndex !== null && optionIndex === item.answer_index
    const points = scoreQuizRushAnswer(correct, timeRemaining, perQuestion, streak)
    const nextScore = capScore(score + points, maxScore)
    setScore(nextScore)
    setStreak(correct ? streak + 1 : 0)
    if (index + 1 >= items.length) {
      finish(nextScore)
    } else {
      setIndex(index + 1)
      setTimeRemaining(perQuestion)
    }
  }, [items, index, timeRemaining, perQuestion, streak, score, maxScore, finish])

  React.useEffect(() => {
    if (paused || done) return
    const t = setInterval(() => {
      setTimeRemaining((prev) => {
        if (prev <= 1) {
          answer(null) // time up = wrong
          return perQuestion
        }
        return prev - 1
      })
    }, 1000)
    return () => clearInterval(t)
  }, [paused, done, answer, perQuestion])

  const item = items[Math.min(index, items.length - 1)]

  return (
    <GameShell
      title={title}
      accentClass="text-violet-600"
      currentIndex={index}
      totalItems={items.length}
      score={score}
      maxScore={maxScore}
      timeRemainingS={timeRemaining}
      totalTimeS={perQuestion}
      paused={paused}
      onPauseToggle={() => setPaused((p) => !p)}
      result={done ? { score, maxScore } : null}
      onReplay={() => window.location.reload()}
    >
      <div className="p-4 space-y-4">
        <p className="text-lg font-medium text-gray-900">{item.prompt}</p>
        <div className="grid gap-2 sm:grid-cols-2">
          {item.options.map((option, i) => (
            <button key={i} type="button" onClick={() => answer(i)}
              className="px-4 py-3 rounded-xl border-2 border-gray-200 text-left text-sm hover:border-violet-400 active:scale-[0.98] transition">
              {option}
            </button>
          ))}
        </div>
      </div>
    </GameShell>
  )
}

export default QuizRush
```

  `MatchPairs.tsx`: build a shuffled card grid of `2 × items.length` cards
  (`{pairIndex, side: 'left'|'right', text}`); flip two → match if same pairIndex; track
  `missesByPair: Record<number, number>` (each failed flip touching a pair increments it);
  on match add `scoreMatchPair(missesByPair[pairIndex] ?? 0)`; optional countdown from
  `settings.time_limit_s` (0 = off) finishing the game with the current score.
  `DragSort.tsx`: `DndContext` with category drop zones; on wrong drop bounce the item back
  and increment `wrongAttemptsByItem[i]`; on correct drop add
  `scoreDragSortItem(wrongAttemptsByItem[i] ?? 0)`; done when all items placed.
  `WordBuilder.tsx`: shuffled letter tiles per item (spaces auto-placed), tap-to-place +
  backspace; a Hint button (visible while `hintsUsed < settings.hints_allowed`) reveals the
  next letter; on solve add `scoreWordBuilderItem(hintsUsed)`.
  `SequenceGame.tsx`: `@dnd-kit/sortable` vertical list initialized with a shuffle that is
  re-shuffled if it happens to equal the correct order; Submit compares positions →
  `scoreSequenceSubmit(correctCount, isRetry)`; first submit with any wrong positions offers
  ONE retry (wrong items highlighted); second submit is final.
  Every engine: pure props, `onComplete` exactly once, config strings as React text only,
  `capScore` before reporting.

- [ ] Implement `GamePlayer.tsx`:

```tsx
/**
 * GamePlayer — fetches /games/{id}/play, dispatches to the template's
 * engine, POSTs the advisory result on completion, and fires
 * onLessonComplete AFTER a successful POST when embedded in a lesson.
 * previewOnly (instructor preview) suppresses BOTH — mirrors H5PLesson's
 * semantics exactly. Server-side the same flag is enforced anyway
 * (owner/admin POSTs return {preview: true} without writing).
 */
import * as React from 'react'
import { Loader2, AlertTriangle } from 'lucide-react'
import {
  getGamePlay,
  submitGameResult,
  type GamePlayPayload,
  type QuizRushConfig,
  type MatchPairsConfig,
  type DragSortConfig,
  type WordBuilderConfig,
  type SequenceConfig,
} from '@/api/games'
import { QuizRush, type GameOutcome } from './engines/QuizRush'
import { MatchPairs } from './engines/MatchPairs'
import { DragSort } from './engines/DragSort'
import { WordBuilder } from './engines/WordBuilder'
import { SequenceGame } from './engines/SequenceGame'

export interface GamePlayerProps {
  gameId: number
  previewOnly?: boolean
  onLessonComplete?: () => void
  className?: string
}

export const GamePlayer: React.FC<GamePlayerProps> = ({
  gameId, previewOnly = false, onLessonComplete, className = '',
}) => {
  const [payload, setPayload] = React.useState<GamePlayPayload | null>(null)
  const [error, setError] = React.useState<string | null>(null)
  const completionHandledRef = React.useRef(false)

  React.useEffect(() => {
    completionHandledRef.current = false
    setPayload(null)
    setError(null)
    getGamePlay(gameId)
      .then(setPayload)
      .catch((err: any) =>
        setError(err?.response?.data?.detail || 'This game could not be loaded.'))
  }, [gameId])

  const handleComplete = React.useCallback(async (outcome: GameOutcome) => {
    if (completionHandledRef.current) return
    completionHandledRef.current = true
    if (previewOnly) return
    try {
      await submitGameResult(gameId, {
        score: outcome.score,
        max_score: outcome.maxScore,
        duration_s: outcome.durationS,
      })
      onLessonComplete?.()
    } catch {
      // Advisory data — a failed POST must not break the results screen.
    }
  }, [gameId, previewOnly, onLessonComplete])

  if (error) {
    return (
      <div className={`flex items-center justify-center p-8 text-red-600 ${className}`}>
        <AlertTriangle className="w-5 h-5 mr-2" /> <span className="text-sm">{error}</span>
      </div>
    )
  }
  if (!payload) {
    return (
      <div className={`flex items-center justify-center p-8 text-gray-500 ${className}`}>
        <Loader2 className="w-5 h-5 animate-spin mr-2" />
        <span className="text-sm">Loading game&hellip;</span>
      </div>
    )
  }

  const common = { onComplete: handleComplete, title: payload.title }
  return (
    <div className={`h-full w-full ${className}`}>
      {payload.template === 'quiz_rush' && (
        <QuizRush config={payload.config as QuizRushConfig} {...common} />
      )}
      {payload.template === 'match_pairs' && (
        <MatchPairs config={payload.config as MatchPairsConfig} {...common} />
      )}
      {payload.template === 'drag_sort' && (
        <DragSort config={payload.config as DragSortConfig} {...common} />
      )}
      {payload.template === 'word_builder' && (
        <WordBuilder config={payload.config as WordBuilderConfig} {...common} />
      )}
      {payload.template === 'sequence' && (
        <SequenceGame config={payload.config as SequenceConfig} {...common} />
      )}
    </div>
  )
}

export default GamePlayer
```

- [ ] Run to pass: `npx vitest run src/components/games/__tests__/GamePlayer.test.tsx`;
      `npm run type-check`; grep-gate: `dangerouslySetInnerHTML` must have ZERO matches under
      `frontend/src/components/games/` and `frontend/src/pages/**/game*`.
- [ ] Commit: `feat(games): GameShell, 5 engines, GamePlayer (previewOnly + lesson hook)`

---

## Task 9: GamePicker + three-way content selector in edit-course AND create-course

**Files:**
- Create: `frontend/src/components/games/GamePicker.tsx`
- Modify: `frontend/src/pages/instructor/edit-course.tsx`
- Modify: `frontend/src/pages/instructor/create-course.tsx`
- Test: `frontend/src/components/games/__tests__/GamePicker.test.tsx`

**Interfaces:**
- Produces: `GamePicker: React.FC<{ value?: number | null; onChange: (gameId: number | null) => void; className?: string }>`
  — lists own **published** games via `listMyGames()` + a "Create new game →" link to
  `/instructor/games`.
- Consumes: `listMyGames`, `GameSummary` (Task 7); the lecture state + `updateLecture` plumbing
  from commit 6d937c3's atomic pair sync (both course pages).

**Steps:**

- [ ] Write failing `GamePicker.test.tsx` (mirror `H5PPicker.test.tsx` conventions):

```tsx
import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import * as gamesApi from '@/api/games'
import { GamePicker } from '../GamePicker'

vi.mock('@/api/games', async (importOriginal) => {
  const actual = await importOriginal<typeof gamesApi>()
  return { ...actual, listMyGames: vi.fn() }
})

const summaries: gamesApi.GameSummary[] = [
  { id: 1, owner_id: 9, title: 'Published Game', template: 'quiz_rush', status: 'published',
    item_count: 3, max_score: 30, attached_lesson_count: 0,
    created_at: 'x', updated_at: 'x' },
  { id: 2, owner_id: 9, title: 'Draft Game', template: 'sequence', status: 'draft',
    item_count: 3, max_score: 30, attached_lesson_count: 0,
    created_at: 'x', updated_at: 'x' },
]

describe('GamePicker', () => {
  beforeEach(() => {
    vi.mocked(gamesApi.listMyGames).mockResolvedValue({ games: summaries, count: 2 })
  })

  it('lists only PUBLISHED games as selectable options', async () => {
    render(<MemoryRouter><GamePicker value={null} onChange={() => {}} /></MemoryRouter>)
    await waitFor(() => expect(screen.getByText('Published Game')).toBeInTheDocument())
    expect(screen.queryByText('Draft Game')).not.toBeInTheDocument()
  })

  it('emits the selected game id', async () => {
    const onChange = vi.fn()
    render(<MemoryRouter><GamePicker value={null} onChange={onChange} /></MemoryRouter>)
    await waitFor(() => expect(screen.getByRole('combobox')).toBeInTheDocument())
    fireEvent.change(screen.getByRole('combobox'), { target: { value: '1' } })
    expect(onChange).toHaveBeenCalledWith(1)
  })

  it('links to the games library for creating a new game', async () => {
    render(<MemoryRouter><GamePicker value={null} onChange={() => {}} /></MemoryRouter>)
    await waitFor(() =>
      expect(screen.getByRole('link', { name: /create new game/i }))
        .toHaveAttribute('href', '/instructor/games'))
  })
})
```

- [ ] Implement `GamePicker.tsx`:

```tsx
/**
 * GamePicker — curriculum picker (spec §6): the instructor's own PUBLISHED
 * games + a "Create new game" link into the library. value/onChange carry
 * the Game integer id (the lessons.game_id FK) — mirrors H5PPicker's
 * value semantics.
 */
import * as React from 'react'
import { Link } from 'react-router-dom'
import { Loader2, AlertTriangle, RefreshCw, Gamepad2 } from 'lucide-react'
import { listMyGames, type GameSummary } from '@/api/games'

export interface GamePickerProps {
  value?: number | null
  onChange: (gameId: number | null) => void
  className?: string
}

export const GamePicker: React.FC<GamePickerProps> = ({ value, onChange, className = '' }) => {
  const [games, setGames] = React.useState<GameSummary[]>([])
  const [loading, setLoading] = React.useState(true)
  const [loadError, setLoadError] = React.useState<string | null>(null)

  const refresh = React.useCallback(async () => {
    setLoading(true)
    setLoadError(null)
    try {
      const res = await listMyGames()
      setGames(res.games.filter((g) => g.status === 'published'))
    } catch (err: any) {
      setLoadError(err?.response?.data?.detail || 'Failed to load your games')
    } finally {
      setLoading(false)
    }
  }, [])

  React.useEffect(() => { refresh() }, [refresh])

  return (
    <div className={`space-y-2 ${className}`}>
      <label className="block text-sm font-medium text-gray-700">Select a learning game</label>
      {loading ? (
        <div className="flex items-center gap-2 text-sm text-gray-500">
          <Loader2 className="w-4 h-4 animate-spin" /> Loading your games&hellip;
        </div>
      ) : loadError ? (
        <div className="flex items-center gap-2 text-sm text-red-600">
          <AlertTriangle className="w-4 h-4" /> {loadError}
          <button type="button" onClick={refresh}
            className="ml-2 text-blue-600 hover:underline inline-flex items-center gap-1">
            <RefreshCw className="w-3 h-3" /> Retry
          </button>
        </div>
      ) : (
        <select
          value={value ?? ''}
          onChange={(e) => onChange(e.target.value ? Number(e.target.value) : null)}
          className="w-full px-3 py-2 text-sm border border-gray-300 rounded focus:ring-2 focus:ring-blue-500 focus:border-transparent"
        >
          <option value="">— Choose a published game —</option>
          {games.map((g) => (
            <option key={g.id} value={g.id}>
              {g.title} ({g.template.replace('_', ' ')}, {g.item_count} items)
            </option>
          ))}
        </select>
      )}
      <Link to="/instructor/games"
        className="inline-flex items-center gap-1 text-xs font-medium text-blue-600 hover:underline">
        <Gamepad2 className="w-3.5 h-3.5" /> Create new game &rarr;
      </Link>
    </div>
  )
}

export default GamePicker
```

- [ ] `edit-course.tsx` — three changes (create-course.tsx gets the mirrored set):
  1. Lecture interface (~line 124): `contentType?: 'video' | 'h5p' | 'game'` and add
     `gameId?: number | null` below `h5pContentId`.
  2. Load mapping (~line 246):

```tsx
              contentType: lesson.lesson_content_type === 'h5p' ? 'h5p'
                : lesson.lesson_content_type === 'game' ? 'game' : 'video',
              h5pContentId: lesson.h5p_content_id ?? null,
              gameId: lesson.game_id ?? null,
```

  3. The field-sync switch (~line 563) — **the atomic pair rule from 6d937c3 applies to
     game_id identically**: only the flip back to video syncs alone; 'h5p'/'game' sync
     together with their id once one is picked:

```tsx
        else if (field === 'contentType') {
          // The backend validates (lesson_content_type, h5p_content_id/game_id)
          // as an atomic pair — PATCHing type='h5p' or 'game' alone is a 400.
          // Only the flip back to video syncs here (the server clears both
          // FKs); 'h5p'/'game' sync together with their id below.
          if (value === 'video') updateData.lesson_content_type = 'video'
        }
        else if (field === 'h5pContentId') {
          if (value != null) {
            updateData.lesson_content_type = 'h5p'
            updateData.h5p_content_id = value as number
          }
        }
        else if (field === 'gameId') {
          if (value != null) {
            updateData.lesson_content_type = 'game'
            updateData.game_id = value as number
          }
        }
```

  4. The selector + picker render (~line 1630):

```tsx
                                            <select
                                              value={lecture.contentType || 'video'}
                                              onChange={(e) => {
                                                const nextType = e.target.value as 'video' | 'h5p' | 'game'
                                                updateLecture(section.id, lecture.id, 'contentType', nextType)
                                                if (nextType !== 'h5p') updateLecture(section.id, lecture.id, 'h5pContentId', null)
                                                if (nextType !== 'game') updateLecture(section.id, lecture.id, 'gameId', null)
                                              }}
                                              className="px-3 py-2 text-sm border border-gray-300 rounded focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                                            >
                                              <option value="video">Video</option>
                                              <option value="h5p">H5P interactive</option>
                                              <option value="game">Learning game</option>
                                            </select>
                                          </div>

                                          {lecture.contentType === 'h5p' ? (
                                            <H5PPicker
                                              value={lecture.h5pContentId ?? null}
                                              onChange={(contentId) => updateLecture(section.id, lecture.id, 'h5pContentId', contentId)}
                                            />
                                          ) : lecture.contentType === 'game' ? (
                                            <GamePicker
                                              value={lecture.gameId ?? null}
                                              onChange={(gameId) => updateLecture(section.id, lecture.id, 'gameId', gameId)}
                                            />
                                          ) : (
                                            /* existing VideoUpload branch unchanged */
```

  Add `import { GamePicker } from '@/components/games/GamePicker'` next to the H5PPicker
  import in both files. Apply the same 4 changes to `create-course.tsx` (its equivalents are
  at ~lines 85, 415-427, 1218-1237 — the local-state save path there also builds lesson
  payloads at create time: wherever it emits `lesson_content_type`/`h5p_content_id`, emit the
  game pair identically).

- [ ] Run to pass: `npx vitest run src/components/games/__tests__/GamePicker.test.tsx`;
      `npm run type-check`; `npm run lint`.
- [ ] Commit: `feat(games): GamePicker + three-way Video|H5P|Game selector, atomic game_id sync`

---

## Task 10: Instructor pages (games library + builder with live preview) + routes + nav

**Files:**
- Create: `frontend/src/pages/instructor/games.tsx`
- Create: `frontend/src/pages/instructor/game-builder.tsx`
- Create: `frontend/src/components/games/builderValidation.ts` (+ test)
- Modify: `frontend/src/App.tsx` (routes), `frontend/src/components/dashboard/nav-configs.ts`
  (INSTRUCTOR_NAV — NOT the dead `components/layout/header.tsx`)
- Test: `frontend/src/components/games/__tests__/builderValidation.test.ts`

**Interfaces:**
- Produces:
  - Route `/instructor/games` → `InstructorGamesPage` (template gallery + own-games table)
  - Routes `/instructor/games/new` (reads `?template=X`) and `/instructor/games/:id/edit` →
    `GameBuilderPage`
  - `validateConfigDraft(template: GameTemplate, config: GameConfig): string[]` — client-side
    inline validation mirroring the server caps (returns human-readable errors, [] = valid)
- Consumes: `createGame`, `getGame`, `updateGame`, `publishGame`, `unpublishGame`,
  `deleteGame`, `listMyGames`, `listGameResults` (Task 7); `GamePlayer` with
  `previewOnly` (Task 8).

**Steps:**

- [ ] Write failing `builderValidation.test.ts`:

```typescript
import { describe, expect, it } from 'vitest'
import { validateConfigDraft } from '../builderValidation'

describe('validateConfigDraft', () => {
  it('accepts a valid quiz_rush config', () => {
    expect(validateConfigDraft('quiz_rush', {
      items: [{ prompt: 'Q?', options: ['a', 'b'], answer_index: 0 }],
      settings: { seconds_per_question: 20, shuffle: false },
    })).toEqual([])
  })

  it('flags item-count, option-count, index, and length violations', () => {
    const errors = validateConfigDraft('quiz_rush', {
      items: [{ prompt: 'p'.repeat(501), options: ['only'], answer_index: 5 }],
      settings: { seconds_per_question: 200, shuffle: false },
    })
    expect(errors.length).toBeGreaterThanOrEqual(4)
  })

  it('enforces word_builder answer regex', () => {
    const errors = validateConfigDraft('word_builder', {
      items: [{ clue: 'c', answer: 'bad!char' }],
      settings: { hints_allowed: 0 },
    })
    expect(errors.some((e) => e.includes('letters'))).toBe(true)
  })

  it('enforces per-template item ranges', () => {
    expect(validateConfigDraft('match_pairs', {
      items: [{ left: 'l', right: 'r' }],
      settings: { time_limit_s: 0 },
    }).length).toBeGreaterThan(0)
    expect(validateConfigDraft('sequence', {
      items: [{ text: 'a' }, { text: 'b' }],
      settings: { time_limit_s: 0, shuffle: true },
    }).length).toBeGreaterThan(0)
  })
})
```

- [ ] Implement `builderValidation.ts` — client-side mirror of
      `backend/app/schemas/game_config.py`'s caps (server remains authoritative; this is
      inline UX only):

```typescript
/** Client-side inline validation mirroring the server caps in
 * backend/app/schemas/game_config.py (spec §1). Returns human-readable
 * errors; [] = valid. The SERVER is authoritative — this only powers the
 * builder's inline error hints and Save-button gating. */
import type {
  DragSortConfig,
  GameConfig,
  GameTemplate,
  MatchPairsConfig,
  QuizRushConfig,
  SequenceConfig,
  WordBuilderConfig,
} from '@/api/games'

export const MAX_CONFIG_BYTES = 64 * 1024
export const MAX_ITEM_STRING = 500
export const MAX_OPTION_STRING = 200
export const WORD_BUILDER_ANSWER_RE = /^[A-Za-z0-9 ]{2,24}$/

function checkStr(errors: string[], value: string, label: string, max = MAX_ITEM_STRING) {
  if (!value || !value.trim()) errors.push(`${label} is required`)
  else if (value.length > max) errors.push(`${label} must be at most ${max} characters`)
}

function checkRange(errors: string[], value: number, min: number, max: number, label: string) {
  if (!Number.isInteger(value) || value < min || value > max) {
    errors.push(`${label} must be between ${min} and ${max}`)
  }
}

export function validateConfigDraft(template: GameTemplate, config: GameConfig): string[] {
  const errors: string[] = []
  if (new Blob([JSON.stringify(config)]).size > MAX_CONFIG_BYTES) {
    errors.push('Game is too large (64KB config limit) — remove some items')
  }

  if (template === 'quiz_rush') {
    const c = config as QuizRushConfig
    checkRange(errors, c.items.length, 1, 50, 'Question count')
    c.items.forEach((item, i) => {
      checkStr(errors, item.prompt, `Question ${i + 1} prompt`)
      if (item.options.length < 2 || item.options.length > 6) {
        errors.push(`Question ${i + 1} needs 2 to 6 options`)
      }
      item.options.forEach((o, j) =>
        checkStr(errors, o, `Question ${i + 1} option ${j + 1}`, MAX_OPTION_STRING))
      if (item.answer_index < 0 || item.answer_index >= item.options.length) {
        errors.push(`Question ${i + 1} has no valid correct answer selected`)
      }
    })
    checkRange(errors, c.settings.seconds_per_question, 5, 120, 'Seconds per question')
  } else if (template === 'match_pairs') {
    const c = config as MatchPairsConfig
    checkRange(errors, c.items.length, 3, 12, 'Pair count')
    c.items.forEach((item, i) => {
      checkStr(errors, item.left, `Pair ${i + 1} left side`)
      checkStr(errors, item.right, `Pair ${i + 1} right side`)
    })
    checkRange(errors, c.settings.time_limit_s, 0, 600, 'Time limit')
  } else if (template === 'drag_sort') {
    const c = config as DragSortConfig
    checkRange(errors, c.categories.length, 2, 5, 'Category count')
    c.categories.forEach((cat, i) => checkStr(errors, cat.name, `Category ${i + 1} name`))
    checkRange(errors, c.items.length, 4, 40, 'Item count')
    c.items.forEach((item, i) => {
      checkStr(errors, item.text, `Item ${i + 1} text`)
      if (item.category_index < 0 || item.category_index >= c.categories.length) {
        errors.push(`Item ${i + 1} points at a missing category`)
      }
    })
    checkRange(errors, c.settings.time_limit_s, 0, 600, 'Time limit')
  } else if (template === 'word_builder') {
    const c = config as WordBuilderConfig
    checkRange(errors, c.items.length, 1, 20, 'Word count')
    c.items.forEach((item, i) => {
      checkStr(errors, item.clue, `Word ${i + 1} clue`)
      if (!WORD_BUILDER_ANSWER_RE.test(item.answer)) {
        errors.push(`Word ${i + 1} answer must be 2-24 letters, digits or spaces`)
      }
    })
    checkRange(errors, c.settings.hints_allowed, 0, 3, 'Hints allowed')
  } else if (template === 'sequence') {
    const c = config as SequenceConfig
    checkRange(errors, c.items.length, 3, 10, 'Step count')
    c.items.forEach((item, i) => checkStr(errors, item.text, `Step ${i + 1}`))
    checkRange(errors, c.settings.time_limit_s, 0, 600, 'Time limit')
  }

  return errors
}
```
- [ ] Implement `pages/instructor/games.tsx` (`InstructorGamesPage`): template gallery of 5
      cards (name, one-line description, inline-SVG illustration per template, accent color,
      "Use this template" → `/instructor/games/new?template=quiz_rush` etc.), plus own-games
      table from `listMyGames()` (title, template, status chip, item_count,
      attached_lesson_count, updated_at; per-row actions Edit → builder,
      Publish/Unpublish via `publishGame`/`unpublishGame` — surface 409 details in a toast —
      Delete via `deleteGame` behind a confirm, Results drawer via `listGameResults` showing
      per-student best/attempts/last-played). Follow the layout conventions of
      `pages/instructor/courses.tsx` (Card/Button/Badge from `@/components/ui`).
- [ ] Implement `pages/instructor/game-builder.tsx` (`GameBuilderPage`): reads
      `useParams().id` (edit) or `useSearchParams().get('template')` (new). Layout:
      left settings panel (title input + per-template settings fields) + per-template item
      editor (add/remove/reorder rows; per-field inline errors from
      `validateConfigDraft`, live-updated) + right **live preview** pane. Live preview runs
      the REAL engine components directly with the local draft config and `previewOnly`
      semantics: render the engine (e.g. `<QuizRush config={draft} onComplete={() => {}} />`)
      keyed by a `previewNonce` state so "Restart preview" remounts it — no network, no
      result POST (engines are pure props; the POST lives only in GamePlayer). Save =
      `createGame`/`updateGame` (button disabled while `validateConfigDraft` returns
      errors); Publish = save then `publishGame`, surfacing server 400 details verbatim.
- [ ] Routes in `App.tsx` (next to the instructor course routes, same
      `ProtectedRoute`/`InstructorLayout` wrappers used at ~line 604 — copy the exact
      wrapper element pattern used there):

```tsx
import InstructorGamesPage from '@/pages/instructor/games'
import GameBuilderPage from '@/pages/instructor/game-builder'
// ...
              <Route path="/instructor/games" element={
                /* same guard+layout wrapper as /instructor/courses */
                <InstructorLayout><InstructorGamesPage /></InstructorLayout>
              } />
              <Route path="/instructor/games/new" element={
                <InstructorLayout><GameBuilderPage /></InstructorLayout>
              } />
              <Route path="/instructor/games/:id/edit" element={
                <InstructorLayout><GameBuilderPage /></InstructorLayout>
              } />
```

- [ ] Nav: in `frontend/src/components/dashboard/nav-configs.ts` `INSTRUCTOR_NAV`, insert
      after the Certificates entry (import `Gamepad2` from lucide-react at the top):

```typescript
  { kind: 'link', to: '/instructor/games', label: 'Games', icon: Gamepad2, matchPrefix: '/instructor/games' },
```

- [ ] Run to pass: `npx vitest run src/components/games/__tests__/builderValidation.test.ts`;
      `npm run type-check`; `npm run lint`.
- [ ] Commit: `feat(games): instructor library + builder with live preview, routes, nav`

---

## Task 11: Student play route + lesson-redesigned game branch

**Files:**
- Create: `frontend/src/pages/game-play.tsx`
- Modify: `frontend/src/App.tsx` (student route `/games/:id/play`)
- Modify: `frontend/src/pages/lesson-redesigned.tsx` (game branch + completion hook + payload
  fields)

**Interfaces:**
- Consumes: `GamePlayer` (Task 8); lesson payload fields `game_id`/`game_title`
  (Task 6 backend); the EXACT H5P completion mechanism already in lesson-redesigned.tsx
  (`handleH5PCompleted` at ~line 1670: guard ref → `POST
  /courses/{courseId}/lessons/{lessonId}/complete` → `markLessonCompleteLocally` →
  `fetchCourse` → achievement notification).

**Steps:**

- [ ] Implement `pages/game-play.tsx` (standalone student route):

```tsx
/** Standalone game play page — /games/:id/play (spec §6). The backend's
 * play gate does all authorization; this page just hosts GamePlayer. */
import * as React from 'react'
import { useParams } from 'react-router-dom'
import { GamePlayer } from '@/components/games/GamePlayer'

export const GamePlayPage: React.FC = () => {
  const { id } = useParams<{ id: string }>()
  const gameId = Number(id)
  if (!Number.isInteger(gameId) || gameId <= 0) {
    return <div className="p-8 text-center text-red-600">Invalid game link.</div>
  }
  return (
    <div className="max-w-3xl mx-auto min-h-[70vh] py-6 px-4">
      <GamePlayer gameId={gameId} className="min-h-[60vh]" />
    </div>
  )
}

export default GamePlayPage
```

  Route in `App.tsx`, wrapped the same way the other authenticated student pages are
  (find the `/leaderboard` route and copy its guard/layout wrapper exactly):

```tsx
import GamePlayPage from '@/pages/game-play'
// ...
              <Route path="/games/:id/play" element={
                /* same guard+layout wrapper as /leaderboard */
                <GamePlayPage />
              } />
```

- [ ] `lesson-redesigned.tsx` — four edits, mirroring the H5P wiring point-for-point:
  1. Import: `import { GamePlayer } from "@/components/games/GamePlayer"` (next to the
     H5PLesson import, line 46).
  2. Both lesson-payload mappings (~lines 1024-1028 and 1090-1093) gain:

```tsx
            game_id: currentLesson.game_id ?? null,
            game_title: currentLesson.game_title ?? null,
```

  3. Completion handler — **EXACTLY the H5P mechanism** (copy `handleH5PCompleted`,
     ~lines 1668-1688, renamed; same guard ref, same complete endpoint, same local mark +
     refetch + achievement toasts):

```tsx
  // Learning-game completion (spec §5): reuse the H5P lesson-complete
  // mechanism EXACTLY — GamePlayer already POSTed the advisory result
  // before calling this. Game lessons therefore count in
  // calculate_course_progress with zero new progress infrastructure.
  const gameCompletionHandledRef = React.useRef(false)
  React.useEffect(() => { gameCompletionHandledRef.current = false }, [lessonId])
  const handleGameCompleted = React.useCallback(async () => {
    if (gameCompletionHandledRef.current) return
    gameCompletionHandledRef.current = true
    if (!lesson?.id || !currentCourseId || lesson.type !== 'lesson') return

    try {
      const response = await api.post(`/courses/${numericCourseId || currentCourseId}/lessons/${lesson.id}/complete`)
      markLessonCompleteLocally(lesson.id)
      await fetchCourse()

      if (response.data.course_completed && response.data.certificate_available) {
        showAchievementNotification('Course completed!', 'Your certificate is ready.', '🎉')
      } else {
        showAchievementNotification('Lesson completed!', 'Great work — keep going.', '✅')
      }
    } catch (error: any) {
      console.error('Error marking game lesson as complete:', error)
    }
  }, [lesson?.id, lesson?.type, currentCourseId, numericCourseId, fetchCourse])
```

  4. Render branch (~line 1918), alongside the existing h5p branch:

```tsx
              ) : lesson.type === 'lesson' && lesson.lesson_content_type === 'game' && lesson.game_id ? (
                <GamePlayer
                  gameId={lesson.game_id}
                  onLessonComplete={handleGameCompleted}
                  className="min-h-[60vh]"
                />
```

- [ ] Verify: `npm run type-check`; `npm run lint`; `npx vitest run` (all games tests green).
- [ ] Commit: `feat(games): student play route + game lesson branch reusing H5P completion flow`

---

## Task 12: Seed script + docs/LEARNING_GAMES.md + CLAUDE.md entry

**Files:**
- Create: `backend/seed_games_demo.py`
- Create: `docs/LEARNING_GAMES.md`
- Modify: `CLAUDE.md` (worktree root — "Notes for future work" list)

**Steps:**

- [ ] Implement `backend/seed_games_demo.py` (mirrors `seed_assessment_demo.py`'s env
      bootstrap + idempotent-ish title checks; one published game per template owned by
      priya@sashademo.com; the quiz_rush one attached to course 1 as a lesson):

```python
"""Demo learning games for the walkthrough. Throwaway.

Creates one PUBLISHED game per template, owned by priya@sashademo.com, and
attaches the quiz_rush game to course 1 as a 'game' lesson. Idempotent-ish:
skips creation when a game with the same title exists.
"""
import os

os.environ.setdefault("DATABASE_URL", "sqlite:///./visual_qa.db")
os.environ.setdefault("REDIS_URL", "redis://127.0.0.1:6379/0?socket_connect_timeout=0.05")
os.environ.setdefault("SECRET_KEY", "x" * 64)
os.environ.setdefault("JWT_SECRET", "y" * 64)
os.environ.setdefault("VIDEO_SECRET", "visual-qa-secret-0123456789abcdef")
os.environ.setdefault("ENVIRONMENT", "development")

from app.core.database import SessionLocal
from app.models.course import Lesson
from app.models.game import Game
from app.models.user import User
from app.schemas.game_config import validate_game_config

COURSE_ID = 1

DEMO_GAMES = {
    "quiz_rush": ("HTML Basics Rush", {
        "items": [
            {"prompt": "Which tag makes a hyperlink?", "options": ["<a>", "<p>", "<div>"], "answer_index": 0},
            {"prompt": "Which tag shows an image?", "options": ["<img>", "<span>"], "answer_index": 0},
            {"prompt": "Where does <title> live?", "options": ["<head>", "<body>", "<footer>"], "answer_index": 0},
        ],
        "settings": {"seconds_per_question": 15, "shuffle": True},
    }),
    "match_pairs": ("CSS Property Match", {
        "items": [
            {"left": "color", "right": "Text color"},
            {"left": "margin", "right": "Space outside the box"},
            {"left": "padding", "right": "Space inside the box"},
        ],
        "settings": {"time_limit_s": 0},
    }),
    "drag_sort": ("Frontend vs Backend", {
        "categories": [{"name": "Frontend"}, {"name": "Backend"}],
        "items": [
            {"text": "React", "category_index": 0},
            {"text": "Tailwind", "category_index": 0},
            {"text": "FastAPI", "category_index": 1},
            {"text": "PostgreSQL", "category_index": 1},
        ],
        "settings": {"time_limit_s": 120},
    }),
    "word_builder": ("Spell the Keyword", {
        "items": [
            {"clue": "Python web framework used by this LMS", "answer": "fastapi"},
            {"clue": "Language of the browser", "answer": "javascript"},
        ],
        "settings": {"hints_allowed": 2},
    }),
    "sequence": ("HTTP Request Lifecycle", {
        "items": [
            {"text": "Browser sends the request"},
            {"text": "Server routes to a handler"},
            {"text": "Handler queries the database"},
            {"text": "Response is rendered"},
        ],
        "settings": {"time_limit_s": 0, "shuffle": True},
    }),
}


def main():
    db = SessionLocal()
    instructor = db.query(User).filter(User.user_email == "priya@sashademo.com").first()
    if not instructor:
        print("priya@sashademo.com not found — run the demo user seed first.")
        return

    games_by_template = {}
    for template, (title, config) in DEMO_GAMES.items():
        validate_game_config(template, config)  # fail loudly on drift from the schemas
        game = db.query(Game).filter(Game.title == title).first()
        if not game:
            game = Game(owner_id=instructor.id, title=title, template=template,
                        config=config, status="published")
            db.add(game)
            db.commit()
            db.refresh(game)
            print(f"game created: {template} -> {game.id}")
        else:
            print(f"game exists: {template} -> {game.id}")
        games_by_template[template] = game

    lesson_title = "Play: HTML Basics Rush"
    lesson = db.query(Lesson).filter(
        Lesson.post_parent == COURSE_ID, Lesson.post_title == lesson_title).first()
    if not lesson:
        lesson = Lesson(
            post_author=instructor.id,
            post_parent=COURSE_ID,
            post_title=lesson_title,
            post_content="",
            lesson_content_type="game",
            game_id=games_by_template["quiz_rush"].id,
        )
        db.add(lesson)
        db.commit()
        print(f"game lesson created on course {COURSE_ID}: {lesson.id}")
    else:
        print(f"game lesson exists: {lesson.id}")


if __name__ == "__main__":
    main()
```

- [ ] Write `docs/LEARNING_GAMES.md` with these sections (each fully written out, sourced
      from the spec + the code as built):
  1. **Overview & why native** (vs H5P) — one paragraph.
  2. **Instructor guide** — create from a template, item editor + live preview, publish,
     attach to a lesson via the three-way content selector, read results.
  3. **Template config reference** — the spec §1 table verbatim (all 5 templates: gameplay,
     config shape, caps) + the derived `max_score = 10 × item count` rule + the scoring
     interpretations from this plan's "Resolved spec ambiguities".
  4. **API reference** — every `/api/v1/games` endpoint with method, auth, request/response
     shape, and the 400/403/404/409 rules (from Tasks 3–4).
  5. **Security model** — untrusted-config posture (strict pydantic, 64KB, unknown-key
     rejection, React-text-only rendering, no dangerouslySetInnerHTML), ownership matrix,
     advisory-scores-never-gradebook, server-derived max + clamping.
  6. **XP & lesson completion** — event keys/points, `game_on` badge, the reused H5P
     lesson-complete flow.
  7. **Ops** — `alembic upgrade head` (revision 0004), `seed_games_demo.py` usage, the
     `'/games'` noSlashEndpoints requirement.
- [ ] Append to `CLAUDE.md`'s "Notes for future work" list:

```markdown
- **Learning Games** (2026-09): native instructor-built games (5 templates:
  quiz_rush/match_pairs/drag_sort/word_builder/sequence). One JSON config per
  game, strict per-template pydantic validation (64KB cap, unknown keys
  rejected — app/schemas/game_config.py); max_score always derived
  server-side as 10 x item count. Models app/models/game.py; router
  app/routers/games.py at /api/v1/games; migration
  backend/alembic/versions/0004_learning_games.py (guarded, batch_alter_table
  for lessons.game_id on SQLite). Lessons attach via lesson_content_type=
  'game' + game_id — validated as an ATOMIC PAIR by courses.py's
  _resolve_lesson_content_fields (never PATCH the type without its id).
  Scores are advisory only (grading is client-side; /play ships answers) —
  NEVER gradebook truth. XP via gamification_service.award() — flush-only,
  caller commits, best-effort try/except; event keys
  game:{id}:completed:user:{uid} (+20) / game:{id}:perfect:user:{uid} (+10);
  badge game_on. Traps: '/games' must stay in axios.ts noSlashEndpoints
  (redirect_slashes=False); no dangerouslySetInnerHTML anywhere under
  frontend/src/components/games/ (instructor config is untrusted). Frontend:
  api/games.ts, components/games/ (GameShell, engines/, GamePlayer,
  GamePicker), pages/instructor/games.tsx + game-builder.tsx,
  pages/game-play.tsx; docs/LEARNING_GAMES.md.
```

- [ ] Run the seed against a dev DB to smoke it (optional if no dev DB is up — it is a
      throwaway script; at minimum `./.venv/Scripts/python -c "import seed_games_demo"` must
      import cleanly with the env defaults).
- [ ] Final verification sweep:
  - `./.venv/Scripts/python -m pytest tests/ -v` — zero new failures vs baseline.
  - `npx vitest run` — green.
  - `npm run type-check` && `npm run lint` — zero new issues.
  - `grep -r dangerouslySetInnerHTML frontend/src/components/games frontend/src/pages/instructor/games.tsx frontend/src/pages/instructor/game-builder.tsx frontend/src/pages/game-play.tsx` — zero matches.
- [ ] Commit: `docs(games): demo seed, LEARNING_GAMES.md, CLAUDE.md entry`

---

## Spec coverage map (self-review)

| Spec section | Covered by |
|---|---|
| §1 templates + validation caps | Tasks 2 (server), 7 (scoring), 10 (builder validation) |
| §2 data model + migration 0004 | Task 1 |
| §3 API (CRUD, publish rules, results, play gate, noSlash) | Tasks 3, 4, 7 (axios) |
| §3 lesson attach pair rules | Task 6 |
| §4 XP integration + game_on badge | Task 5 |
| §5 lesson completion (H5P mechanism reuse) | Task 11 |
| §6 frontend (api client, GameShell, engines, GamePlayer, GamePicker, pages, nav, routes) | Tasks 7, 8, 9, 10, 11 |
| §7 security summary | Tasks 2 (validation), 3/4 (ownership + clamping), 8 (React-text-only), Global Constraints 4/7 |
| §8 tests (binding matrix) | test additions in Tasks 1–6 (backend), 7–10 (frontend) |
| §9 docs & seed | Task 12 |
| Out of scope | untouched (no gradebook games, no multiplayer, no AI content, no marketplace, no custom templates) |
