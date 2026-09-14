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


# ============================================================================
# Task 2 — Fix round 1: reviewer-confirmed findings (F1-F5, F7) + high-value
# adversarial cases the reviewer named.
# ============================================================================

class TestConfigValidationHardening:
    # ---- F1 CRITICAL: bool/string coercion into int index fields ----------

    def test_answer_index_rejects_bool_true(self):
        cfg = _valid_quiz_rush_config()
        cfg["items"][0]["answer_index"] = True
        with pytest.raises(GameConfigError):
            validate_game_config("quiz_rush", cfg)

    def test_answer_index_rejects_bool_false(self):
        cfg = _valid_quiz_rush_config()
        cfg["items"][0]["answer_index"] = False
        with pytest.raises(GameConfigError):
            validate_game_config("quiz_rush", cfg)

    @pytest.mark.parametrize("bad", ["1", " 1 ", "01", "+1", "0_1"])
    def test_answer_index_rejects_string_coercions(self, bad):
        cfg = _valid_quiz_rush_config()
        cfg["items"][0]["answer_index"] = bad
        with pytest.raises(GameConfigError):
            validate_game_config("quiz_rush", cfg)

    def test_answer_index_rejects_negative(self):
        cfg = _valid_quiz_rush_config()
        cfg["items"][0]["answer_index"] = -1
        with pytest.raises(GameConfigError):
            validate_game_config("quiz_rush", cfg)

    def test_category_index_rejects_bool_true(self):
        cfg = _valid_drag_sort_config()
        cfg["items"][0]["category_index"] = True
        with pytest.raises(GameConfigError):
            validate_game_config("drag_sort", cfg)

    @pytest.mark.parametrize("bad", ["1", " 1 ", "01", "+1", "0_1"])
    def test_category_index_rejects_string_coercions(self, bad):
        cfg = _valid_drag_sort_config()
        cfg["items"][0]["category_index"] = bad
        with pytest.raises(GameConfigError):
            validate_game_config("drag_sort", cfg)

    def test_category_index_rejects_negative(self):
        cfg = _valid_drag_sort_config()
        cfg["items"][0]["category_index"] = -1
        with pytest.raises(GameConfigError):
            validate_game_config("drag_sort", cfg)

    # ---- F2 IMPORTANT: word_builder regex trailing-newline bypass ---------

    def test_word_builder_answer_regex_rejects_trailing_newline(self):
        # Unit-test the compiled pattern directly: this is the exact string
        # the reviewer confirmed was wrongly ACCEPTED by re.match(pattern +
        # "$") (Python's `$` matches immediately before a trailing "\n"),
        # violating the binding 2..24-char cap (25 chars including the
        # newline). fullmatch (module fix) must reject it.
        from app.schemas.game_config import WORD_BUILDER_ANSWER_RE
        bad = "a" * 24 + "\n"
        assert WORD_BUILDER_ANSWER_RE.fullmatch(bad) is None

    def test_word_builder_answer_rejects_embedded_disallowed_char(self):
        # End-to-end: an answer with a disallowed character that survives
        # F5's strip() (not leading/trailing whitespace) must still be
        # rejected by the regex.
        cfg = _valid_word_builder_config()
        cfg["items"][0]["answer"] = "bad!word"
        with pytest.raises(GameConfigError):
            validate_game_config("word_builder", cfg)

    def test_word_builder_answer_trailing_newline_normalized_by_strip(self):
        # End-to-end: F5's strip() runs before the F2 regex check, so a
        # *trailing* newline is normalized away first (as intended -- it's
        # whitespace) and the now-clean 24-char answer is accepted. This
        # documents the interaction between F5 (strip) and F2 (fullmatch):
        # F2's bug was that the trailing newline survived un-stripped and
        # still matched under old `$` semantics; here it is legitimately
        # stripped, not exploiting the anchor bug.
        cfg = _valid_word_builder_config()
        cfg["items"][0]["answer"] = "a" * 24 + "\n"
        normalized = validate_game_config("word_builder", cfg)
        assert normalized["items"][0]["answer"] == "a" * 24

    # ---- F3 IMPORTANT: truthy non-bool coercion into bool fields ----------

    @pytest.mark.parametrize("truthy", ["yes", 1, "true", "1"])
    def test_sequence_shuffle_rejects_truthy_non_bool(self, truthy):
        cfg = _valid_sequence_config()
        cfg["settings"]["shuffle"] = truthy
        with pytest.raises(GameConfigError):
            validate_game_config("sequence", cfg)

    @pytest.mark.parametrize("truthy", ["yes", 1, "true", "0", 0])
    def test_quiz_rush_shuffle_rejects_non_bool(self, truthy):
        cfg = _valid_quiz_rush_config()
        cfg["settings"]["shuffle"] = truthy
        with pytest.raises(GameConfigError):
            validate_game_config("quiz_rush", cfg)

    # ---- F5: strip() display strings; reject empty-after-strip ------------

    def test_quiz_rush_prompt_all_whitespace_rejected(self):
        cfg = _valid_quiz_rush_config()
        cfg["items"][0]["prompt"] = " " * 500
        with pytest.raises(GameConfigError):
            validate_game_config("quiz_rush", cfg)

    def test_word_builder_answer_all_whitespace_rejected(self):
        cfg = _valid_word_builder_config()
        cfg["items"][0]["answer"] = "  "
        with pytest.raises(GameConfigError):
            validate_game_config("word_builder", cfg)

    def test_quiz_rush_prompt_is_stripped(self):
        cfg = _valid_quiz_rush_config()
        cfg["items"][0]["prompt"] = "  Question?  "
        normalized = validate_game_config("quiz_rush", cfg)
        assert normalized["items"][0]["prompt"] == "Question?"

    # ---- F7: derive_max_score validates its template arg -------------------

    def test_derive_max_score_rejects_mismatched_template(self):
        # match_pairs config has no 'category_index' etc., but the key point
        # per F7 is that derive_max_score must not silently score an
        # unvalidated / wrong-shaped config for the given template.
        cfg = {"not_items": []}
        with pytest.raises(GameConfigError):
            derive_max_score("quiz_rush", cfg)

    def test_derive_max_score_rejects_unknown_template(self):
        with pytest.raises(GameConfigError):
            derive_max_score("tetris", _valid_quiz_rush_config())

    # ---- adversarial top-level types ---------------------------------------

    @pytest.mark.parametrize("bad_config", [None, 1, "x", []])
    def test_validate_game_config_rejects_non_dict_top_level(self, bad_config):
        with pytest.raises(GameConfigError):
            validate_game_config("quiz_rush", bad_config)

    # ---- unknown key nested inside settings --------------------------------

    def test_unknown_key_inside_settings_rejected(self):
        cfg = _valid_quiz_rush_config()
        cfg["settings"]["evil"] = True
        with pytest.raises(GameConfigError):
            validate_game_config("quiz_rush", cfg)

    # ---- F4: char vs byte semantics documented, multi-byte string ----------

    def test_multibyte_500_char_string_accepted_by_char_cap(self):
        # 500 emoji chars = 500 chars (under MAX_ITEM_STRING's char cap) but
        # ~2000 UTF-8 bytes -- documents that the per-string cap is CHARACTER
        # count, not bytes. The 64KB global cap is the actual byte backstop.
        cfg = _valid_quiz_rush_config()
        cfg["items"][0]["prompt"] = "\U0001F600" * 500
        normalized = validate_game_config("quiz_rush", cfg)
        assert len(normalized["items"][0]["prompt"]) == 500

    # ---- byte-cap boundary probes (existing oversize test uses ~1MB) -------

    @staticmethod
    def _boundary_cfg(opt_len):
        # 50 items (the template max) x 6 options (the per-item max) x
        # opt_len-char options x 500-char prompts. opt_len=122 lands a few
        # hundred bytes UNDER MAX_CONFIG_BYTES; opt_len=123 lands a few
        # dozen bytes OVER it -- both stay within every per-field cap
        # (prompt <=500, option <=200, options <=6, items <=50), so only
        # the byte cap is being probed, nothing else.
        return {
            "items": [
                {"prompt": "P" * 500, "options": ["O" * opt_len] * 6, "answer_index": 0}
                for _ in range(50)
            ],
            "settings": {"seconds_per_question": 20, "shuffle": True},
        }

    def test_config_just_under_byte_cap_accepted(self):
        import json
        cfg = self._boundary_cfg(opt_len=122)
        serialized_len = len(json.dumps(cfg).encode())
        assert serialized_len < MAX_CONFIG_BYTES
        assert MAX_CONFIG_BYTES - serialized_len < 500
        normalized = validate_game_config("quiz_rush", cfg)
        assert isinstance(normalized, dict)

    def test_config_just_over_byte_cap_rejected(self):
        import json
        cfg = self._boundary_cfg(opt_len=123)
        serialized_len = len(json.dumps(cfg).encode())
        assert serialized_len > MAX_CONFIG_BYTES
        assert serialized_len - MAX_CONFIG_BYTES < 500
        with pytest.raises(GameConfigError):
            validate_game_config("quiz_rush", cfg)


# ----- admin auth helper (copied verbatim from tests/test_h5p.py) -----------

def _admin_headers(client, db, admin):
    """Admin logins require TOTP 2FA — enrol a secret and send the current
    code (mirrors test_assessment_integrity._admin_headers)."""
    import pyotp
    from app.core import totp

    admin.totp_enabled = True
    admin.totp_secret = totp.generate_secret()
    db.commit()
    r = client.post(
        "/api/v1/auth/login",
        json={
            "email": admin.user_email,
            "password": admin._test_password,
            "otp_code": pyotp.TOTP(admin.totp_secret).now(),
        },
    )
    assert r.status_code == 200, r.text
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


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

    # ----- ownership-matrix gaps carried from Task 3 review ------------------

    def test_student_blocked_from_get_put(self, client, db, make_user, auth_headers):
        owner = _make_approved_instructor(db, make_user, "crud-j@example.com")
        game = _make_game(db, owner, status="published")
        student = make_user(role="student", email="crud-stu-j@example.com")
        headers = auth_headers(student.user_email)
        assert client.get(f"/api/v1/games/{game.id}", headers=headers).status_code == 403
        assert client.put(f"/api/v1/games/{game.id}", json={"title": "x"},
                          headers=headers).status_code == 403

    def test_student_blocked_from_delete(self, client, db, make_user, auth_headers):
        owner = _make_approved_instructor(db, make_user, "crud-k@example.com")
        game = _make_game(db, owner)
        student = make_user(role="student", email="crud-stu-k@example.com")
        r = client.delete(f"/api/v1/games/{game.id}", headers=auth_headers(student.user_email))
        assert r.status_code == 403

    def test_publish_blocked_for_other_instructor_and_student(self, client, db, make_user, auth_headers):
        owner = _make_approved_instructor(db, make_user, "crud-l@example.com")
        other = _make_approved_instructor(db, make_user, "crud-m@example.com")
        student = make_user(role="student", email="crud-stu-l@example.com")
        game = _make_game(db, owner)

        r = client.post(f"/api/v1/games/{game.id}/publish", headers=auth_headers(other.user_email))
        assert r.status_code == 403
        r2 = client.post(f"/api/v1/games/{game.id}/publish", headers=auth_headers(student.user_email))
        assert r2.status_code == 403

    def test_unpublish_blocked_for_other_instructor_and_student(self, client, db, make_user, auth_headers):
        owner = _make_approved_instructor(db, make_user, "crud-n@example.com")
        other = _make_approved_instructor(db, make_user, "crud-o@example.com")
        student = make_user(role="student", email="crud-stu-n@example.com")
        game = _make_game(db, owner, status="published")

        r = client.post(f"/api/v1/games/{game.id}/unpublish", headers=auth_headers(other.user_email))
        assert r.status_code == 403
        r2 = client.post(f"/api/v1/games/{game.id}/unpublish", headers=auth_headers(student.user_email))
        assert r2.status_code == 403

    def test_mine_requires_instructor_not_student(self, client, db, make_user, auth_headers):
        student = make_user(role="student", email="crud-stu-o@example.com")
        r = client.get("/api/v1/games/mine", headers=auth_headers(student.user_email))
        assert r.status_code == 403


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

    def test_results_rollup_blocked_for_student(self, client, db, make_user, auth_headers):
        _, game, _, _, student = _setup_playable(
            db, make_user, "re-i@example.com", "re-stu-i@example.com")
        r = client.get(f"/api/v1/games/{game.id}/results",
                       headers=auth_headers(student.user_email))
        assert r.status_code == 403

    def test_results_rollup_admin_allowed(self, client, db, make_user, auth_headers):
        owner, game, _, _, student = _setup_playable(
            db, make_user, "re-j@example.com", "re-stu-j@example.com")
        client.post(f"/api/v1/games/{game.id}/results",
                    json={"score": 5, "max_score": 20, "duration_s": 10},
                    headers=auth_headers(student.user_email))
        admin = make_user(role="admin", email="re-admin-j@example.com")
        r = client.get(f"/api/v1/games/{game.id}/results", headers=_admin_headers(client, db, admin))
        assert r.status_code == 200
        assert r.json()["count"] == 1

    # ----- Fix round 1: reviewer findings -------------------------------

    def test_bool_score_rejected(self, client, db, make_user, auth_headers):
        """StrictInt: {"score": true} must NOT silently coerce to 1."""
        _, game, _, _, student = _setup_playable(
            db, make_user, "re-k@example.com", "re-stu-k@example.com")
        r = client.post(f"/api/v1/games/{game.id}/results",
                        json={"score": True, "max_score": 20, "duration_s": 5},
                        headers=auth_headers(student.user_email))
        assert r.status_code == 422

    def test_string_score_rejected(self, client, db, make_user, auth_headers):
        """StrictInt: {"score": "15"} must NOT silently coerce to 15."""
        _, game, _, _, student = _setup_playable(
            db, make_user, "re-l@example.com", "re-stu-l@example.com")
        r = client.post(f"/api/v1/games/{game.id}/results",
                        json={"score": "15", "max_score": 20, "duration_s": 5},
                        headers=auth_headers(student.user_email))
        assert r.status_code == 422

    def test_forged_result_persists_derived_values_not_client_values(self, client, db, make_user, auth_headers):
        """Query GameResult directly: a forged {score: 999, max_score: 999}
        must be stored as the server-derived clamped values, not the
        client-submitted ones."""
        _, game, _, _, student = _setup_playable(
            db, make_user, "re-m@example.com", "re-stu-m@example.com")
        r = client.post(f"/api/v1/games/{game.id}/results",
                        json={"score": 999, "max_score": 999, "duration_s": 5},
                        headers=auth_headers(student.user_email))
        assert r.status_code == 200, r.text
        row = db.query(GameResult).filter_by(game_id=game.id, user_id=student.id).one()
        assert row.score == 20
        assert row.max_score == 20

    def test_cancelled_and_suspended_enrollment_blocked(self, client, db, make_user, auth_headers):
        owner = _make_approved_instructor(db, make_user, "re-n@example.com")
        game = _make_game(db, owner, status="published")
        course = _make_course(db, owner, title="Course re-n")
        _make_game_lesson(db, course, game.id)

        cancelled = make_user(role="student", email="re-stu-n1@example.com")
        _enroll(db, cancelled, course, status="cancelled")
        suspended = make_user(role="student", email="re-stu-n2@example.com")
        _enroll(db, suspended, course, status="suspended")

        for user in (cancelled, suspended):
            headers = auth_headers(user.user_email)
            r_play = client.get(f"/api/v1/games/{game.id}/play", headers=headers)
            assert r_play.status_code == 403
            r_post = client.post(f"/api/v1/games/{game.id}/results",
                                 json={"score": 1, "max_score": 20, "duration_s": 5},
                                 headers=headers)
            assert r_post.status_code == 403

    def test_cross_course_enrollment_gate(self, client, db, make_user, auth_headers):
        owner = _make_approved_instructor(db, make_user, "re-o@example.com")
        game = _make_game(db, owner, status="published")
        course_a = _make_course(db, owner, title="Course A re-o")
        course_b = _make_course(db, owner, title="Course B re-o")
        _make_game_lesson(db, course_a, game.id)  # attached to A only

        student = make_user(role="student", email="re-stu-o@example.com")
        _enroll(db, student, course_b)  # enrolled in B, not A
        headers = auth_headers(student.user_email)
        r = client.get(f"/api/v1/games/{game.id}/play", headers=headers)
        assert r.status_code == 403

        _make_game_lesson(db, course_b, game.id)  # now attached to A AND B
        r2 = client.get(f"/api/v1/games/{game.id}/play", headers=headers)
        assert r2.status_code == 200

    def test_rollup_reports_max_score_from_best_scoring_row(self, client, db, make_user, auth_headers):
        """Reviewer's exact scenario: 4-item game scored 40/40 (a perfect
        run), config then shrunk to 1 item (derived max -> 10), second
        attempt scores 10/10 (also perfect, but a strictly SMALLER score
        than 40). The naive independent max(score)/max(max_score) pairing
        would report best_score=40 correctly, but ALSO independently
        computes max(max_score)=max(40,10)=40 -- which happens to be
        right here only because 40's own row already carries the larger
        max_score. Assert the row-correlated pairing explicitly via a
        direct GameResult query as well, to pin down that best_score's
        max_score is 40 (score 40's own row), not any other value, and
        that attempts / count are unaffected by the config edit."""
        owner = _make_approved_instructor(db, make_user, "re-p@example.com")
        game = _make_game(db, owner, status="published", config=_valid_quiz_rush_config(n_items=4))
        course = _make_course(db, owner, title="Course re-p")
        _make_game_lesson(db, course, game.id)
        student = make_user(role="student", email="re-stu-p@example.com")
        _enroll(db, student, course)
        headers = auth_headers(student.user_email)

        r1 = client.post(f"/api/v1/games/{game.id}/results",
                         json={"score": 40, "max_score": 40, "duration_s": 10}, headers=headers)
        assert r1.json()["score"] == 40
        assert r1.json()["max_score"] == 40

        # Owner shrinks the config to 1 item -> derived max drops to 10.
        owner_headers = auth_headers(owner.user_email)
        shrunk = _valid_quiz_rush_config(n_items=1)
        client.put(f"/api/v1/games/{game.id}", json={"config": shrunk}, headers=owner_headers)

        r2 = client.post(f"/api/v1/games/{game.id}/results",
                         json={"score": 10, "max_score": 10, "duration_s": 5}, headers=headers)
        assert r2.json()["score"] == 10
        assert r2.json()["max_score"] == 10

        # Confirm the stored rows independently: one at 40/40, one at 10/10.
        stored = db.query(GameResult).filter_by(
            game_id=game.id, user_id=student.id).order_by(GameResult.id).all()
        assert [(row.score, row.max_score) for row in stored] == [(40, 40), (10, 10)]

        r3 = client.get(f"/api/v1/games/{game.id}/results", headers=owner_headers)
        assert r3.status_code == 200
        rows = r3.json()["results"]
        assert len(rows) == 1
        # best_score is 40, and it MUST pair with max_score 40 (the SAME
        # row) -- not a stale/mismatched max_score from a different row.
        assert rows[0]["best_score"] == 40
        assert rows[0]["max_score"] == 40
        assert rows[0]["attempts"] == 2

    def test_rollup_pairing_not_independent_max_when_best_row_has_smaller_max(
            self, client, db, make_user, auth_headers):
        """Sharper pairing check: the highest SCORE is on the row with the
        SMALLER max_score. An independent max(score)/max(max_score) would
        wrongly report best_score paired with the larger max_score from a
        different (lower-scoring) row. The row-correlated pairing must
        report the max_score that belongs to the best-scoring row."""
        owner = _make_approved_instructor(db, make_user, "re-q@example.com")
        game = _make_game(db, owner, status="published", config=_valid_quiz_rush_config(n_items=4))
        course = _make_course(db, owner, title="Course re-q")
        _make_game_lesson(db, course, game.id)
        student = make_user(role="student", email="re-stu-q@example.com")
        _enroll(db, student, course)
        headers = auth_headers(student.user_email)

        # First attempt on the 4-item config: mediocre score 8/40.
        r1 = client.post(f"/api/v1/games/{game.id}/results",
                         json={"score": 8, "max_score": 40, "duration_s": 10}, headers=headers)
        assert r1.json()["score"] == 8
        assert r1.json()["max_score"] == 40

        # Owner shrinks the config to 1 item -> derived max drops to 10.
        owner_headers = auth_headers(owner.user_email)
        shrunk = _valid_quiz_rush_config(n_items=1)
        client.put(f"/api/v1/games/{game.id}", json={"config": shrunk}, headers=owner_headers)

        # Second attempt on the shrunk config: perfect score 10/10 -- this
        # is now the BEST score (10 > 8) but has the SMALLER max_score.
        r2 = client.post(f"/api/v1/games/{game.id}/results",
                         json={"score": 10, "max_score": 10, "duration_s": 5}, headers=headers)
        assert r2.json()["score"] == 10
        assert r2.json()["max_score"] == 10

        r3 = client.get(f"/api/v1/games/{game.id}/results", headers=owner_headers)
        rows = r3.json()["results"]
        assert len(rows) == 1
        assert rows[0]["best_score"] == 10
        # Naive independent max(max_score) over all rows would give 40
        # here (from the OTHER, lower-scoring row) -- that would be wrong.
        assert rows[0]["max_score"] == 10
        assert rows[0]["attempts"] == 2

    def test_rollup_tiebreak_deterministic_on_same_created_at(
            self, client, db, make_user, auth_headers):
        """Two same-score attempts with an IDENTICAL created_at (SQLite has
        only second-level resolution via server_default=func.now(), so two
        attempts inside the same second tie there) must still resolve
        deterministically -- via GameResult.id.desc() as the final
        tie-break key, not implementation-defined ORDER BY behavior on a
        tied column. Insert both rows directly with the same created_at so
        the tie is forced (not timing-dependent), then re-run the rollup
        query several times to pin that it always reports the max_score of
        the higher-id (later-inserted) row."""
        owner = _make_approved_instructor(db, make_user, "re-r@example.com")
        game = _make_game(db, owner, status="published", config=_valid_quiz_rush_config(n_items=4))
        course = _make_course(db, owner, title="Course re-r")
        _make_game_lesson(db, course, game.id)
        student = make_user(role="student", email="re-stu-r@example.com")
        _enroll(db, student, course)

        from datetime import datetime, timezone
        tied_ts = datetime(2026, 1, 1, tzinfo=timezone.utc)

        # Same score (20), different max_score (config edited between the
        # two attempts), same created_at -- forces the tie explicitly.
        row_a = GameResult(
            game_id=game.id, user_id=student.id,
            score=20, max_score=40, duration_s=10, created_at=tied_ts,
        )
        db.add(row_a)
        db.commit()
        db.refresh(row_a)

        row_b = GameResult(
            game_id=game.id, user_id=student.id,
            score=20, max_score=10, duration_s=5, created_at=tied_ts,
        )
        db.add(row_b)
        db.commit()
        db.refresh(row_b)

        assert row_a.created_at == row_b.created_at
        assert row_b.id > row_a.id  # strictly increasing PK, later insert

        owner_headers = auth_headers(owner.user_email)
        for _ in range(10):
            r = client.get(f"/api/v1/games/{game.id}/results", headers=owner_headers)
            assert r.status_code == 200
            rows = r.json()["results"]
            assert len(rows) == 1
            assert rows[0]["best_score"] == 20
            # Must always be row_b's max_score (higher id = later insert),
            # never row_a's -- deterministic, not implementation-defined.
            assert rows[0]["max_score"] == 10
            assert rows[0]["attempts"] == 2


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

    def test_clamped_perfect_score_awards_perfect_xp(self, client, db, make_user, auth_headers):
        """Carried from Task 5: an over-range submission (score/max_score
        both far above the derived max) must be clamped server-side to the
        derived max BEFORE the perfect-score comparison, so it still counts
        as a perfect play and awards the game_perfect XP event. Pins the
        clamp-then-compare ordering (a clamp-after-compare bug would silently
        drop this bonus)."""
        _, game, _, _, student = _setup_playable(
            db, make_user, "xp-clamp@example.com", "xp-clamp-stu@example.com")
        headers = auth_headers(student.user_email)

        r = client.post(f"/api/v1/games/{game.id}/results",
                        json={"score": 999, "max_score": 999, "duration_s": 30},
                        headers=headers)
        assert r.status_code == 200, r.text
        body = r.json()
        assert body["score"] == 20          # clamped to derived max (10 x 2 items)
        assert body["max_score"] == 20

        perfect = db.query(XpEvent).filter(
            XpEvent.event_key == f"game:{game.id}:perfect:user:{student.id}").all()
        assert len(perfect) == 1
        assert perfect[0].points == 10
        assert db.query(GameResult).filter_by(game_id=game.id).count() == 1

    def test_xp_course_attribution_is_deterministic_lowest_course_id(
            self, client, db, make_user, auth_headers, monkeypatch):
        """When one game is attached to lessons in MULTIPLE courses, XP
        course attribution must be deterministic (the lowest course_id) —
        not next(iter(set)), whose iteration order depends on hash-table
        layout and is NOT guaranteed to be ascending (e.g. {1, 8} iterates
        as [8, 1] in CPython, since 8 lands in the table's first slot).
        Forces that exact adversarial set via monkeypatch so the assertion
        does not depend on incidental id allocation ordering."""
        _, game, _, _, student = _setup_playable(
            db, make_user, "xp-multi@example.com", "xp-multi-stu@example.com")

        monkeypatch.setattr(
            "app.routers.games._course_ids_with_game_lesson",
            lambda db, game_id: {1, 8},
        )

        headers = auth_headers(student.user_email)
        assert self._post_result(client, headers, game.id, 10).status_code == 200

        event = db.query(XpEvent).filter(
            XpEvent.event_key == f"game:{game.id}:completed:user:{student.id}").first()
        assert event is not None
        assert event.course_id == 1


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

    def test_admin_may_attach_any_owners_game(self, client, db, make_user, auth_headers):
        owner = _make_approved_instructor(db, make_user, "la-adm-owner@example.com")
        admin = make_user(role="admin", email="la-adm@example.com")
        course = _make_course(db, admin)
        game = _make_game(db, owner, status="published")
        r = self._create_lesson(client, _admin_headers(client, db, admin), course.id,
                                {"lesson_content_type": "game", "game_id": game.id})
        assert r.status_code == 200, r.text
        assert r.json()["game_id"] == game.id

    def test_unknown_content_type_400(self, client, db, make_user, auth_headers):
        owner = _make_approved_instructor(db, make_user, "la-unk@example.com")
        course = _make_course(db, owner)
        r = self._create_lesson(client, auth_headers(owner.user_email), course.id,
                                {"lesson_content_type": "pdf"})
        assert r.status_code == 422  # schema-level LESSON_CONTENT_TYPES rejection

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

    def test_flip_from_game_to_h5p_clears_game_id(self, client, db, make_user, auth_headers):
        from app.models.h5p import H5PContent
        from app.services.h5p_service import generate_public_id
        owner = _make_approved_instructor(db, make_user, "la-h@example.com")
        headers = auth_headers(owner.user_email)
        course = _make_course(db, owner)
        game = _make_game(db, owner, status="published")
        content = H5PContent(public_id=generate_public_id(), owner_id=owner.id,
                             title="H5P", library="X 1.0", size_bytes=1, status="ready")
        db.add(content)
        db.commit()
        db.refresh(content)

        r = self._create_lesson(client, headers, course.id,
                                {"lesson_content_type": "game", "game_id": game.id})
        lesson_id = r.json()["id"]

        r2 = client.patch(f"/api/v1/courses/{course.id}/lessons/{lesson_id}",
                          json={"lesson_content_type": "h5p", "h5p_content_id": content.id},
                          headers=headers)
        assert r2.status_code == 200, r2.text
        lesson = db.query(Lesson).filter(Lesson.id == lesson_id).first()
        assert lesson.h5p_content_id == content.id and lesson.game_id is None

    def test_flip_from_game_to_video_clears_game_id(self, client, db, make_user, auth_headers):
        owner = _make_approved_instructor(db, make_user, "la-i@example.com")
        headers = auth_headers(owner.user_email)
        course = _make_course(db, owner)
        game = _make_game(db, owner, status="published")

        r = self._create_lesson(client, headers, course.id,
                                {"lesson_content_type": "game", "game_id": game.id})
        lesson_id = r.json()["id"]

        r2 = client.patch(f"/api/v1/courses/{course.id}/lessons/{lesson_id}",
                          json={"lesson_content_type": "video"}, headers=headers)
        assert r2.status_code == 200, r2.text
        lesson = db.query(Lesson).filter(Lesson.id == lesson_id).first()
        assert lesson.lesson_content_type == "video"
        assert lesson.game_id is None and lesson.h5p_content_id is None

    def test_get_course_includes_lesson_game_fields(self, client, db, make_user, auth_headers):
        owner = _make_approved_instructor(db, make_user, "la-j@example.com")
        headers = auth_headers(owner.user_email)
        course = _make_course(db, owner)
        game = _make_game(db, owner, status="published", title="Attach Me")
        _make_game_lesson(db, course, game.id)

        r = client.get(f"/api/v1/courses/{course.id}", headers=headers)
        assert r.status_code == 200, r.text
        lessons = r.json()["lessons"]
        assert lessons[0]["game_id"] == game.id
        assert lessons[0]["game_title"] == "Attach Me"
