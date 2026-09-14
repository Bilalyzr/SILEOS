"""learning experience — assessment integrity hardening (Task 1)

Additive columns for the Learning Experience Platform. This revision is
grown across Tasks 1/4/9 of docs/superpowers/plans/2026-09-02-learning-experience.md
— each task appends its own guarded block; it is unreleased/unmerged until
the whole branch lands, so accumulating changes in one file (rather than a
revision per task) is intentional and safe.

Task 1 (assessment integrity) adds:
  - assignments.late_policy        String(10) default 'allow'
  - assignments.late_penalty_pct   Integer default 0
  - assignments.rubric             JSON, nullable
  - assignment_submissions.is_late         Boolean default False
  - assignment_submissions.rubric_scores   JSON, nullable
  - uq_assignment_user unique constraint on assignment_submissions
    (assignment_id, user_id)

Task 4 (H5P) adds:
  - h5p_contents table (Integer PK, public_id String(32) unique, owner_id FK,
    title, library, size_bytes, status, created_at, updated_at)
  - h5p_results table (Integer PK, content_id FK, user_id FK, score,
    max_score, completed, updated_at, uq_h5p_result_content_user unique
    constraint on (content_id, user_id))
  - lessons.lesson_content_type    String(20) default 'video'
  - lessons.h5p_content_id         Integer, FK -> h5p_contents.id, nullable

Task 6 (certificate designer) adds:
  - certificates.is_global         Boolean default False — a template an
    admin marks usable (read-only) by every instructor, not just its author.

Task 9 (gamification) adds:
  - xp_events table (Integer PK, user_id FK idx, event_key String(120)
    UNIQUE idx, event_type String(40) idx, points, course_id FK nullable
    idx, meta JSON, created_at)
  - user_game_stats table (Integer PK, user_id FK UNIQUE idx, total_xp,
    current_streak, longest_streak, last_active_date Date,
    leaderboard_visible Boolean default True, badges_count, updated_at)
  - badges table (Integer PK, slug String(60) UNIQUE idx, name,
    description, icon String(40), rule_type, rule_value, created_at)
  - user_badges table (Integer PK, user_id FK idx, badge_id FK idx,
    awarded_at, uq_user_badge unique constraint on (user_id, badge_id))

Same dual-path tolerance as 0002: init_db()'s create_all may already have
created these tables/columns via the SQLAlchemy models before Alembic ever
runs (see app/models/assignment.py), so every operation here is guarded
with has_table/has_column/get_indexes-style inspection, mirroring 0002's
guard style.

Revision ID: 0003
Revises: 0002
Create Date: 2026-09-02

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "0003"
down_revision: Union[str, None] = "0002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _has_column(insp, table_name: str, column_name: str) -> bool:
    if not insp.has_table(table_name):
        return False
    return any(col["name"] == column_name for col in insp.get_columns(table_name))


def _has_unique_constraint(insp, table_name: str, constraint_name: str) -> bool:
    if not insp.has_table(table_name):
        return False
    try:
        uniques = insp.get_unique_constraints(table_name)
    except NotImplementedError:
        # Some SQLite reflection paths don't support unique constraint
        # introspection; fall back to checking indexes (SQLite implements
        # UNIQUE constraints as unique indexes under the hood).
        uniques = []
    if any(uc.get("name") == constraint_name for uc in uniques):
        return True
    indexes = insp.get_indexes(table_name)
    return any(ix.get("name") == constraint_name and ix.get("unique") for ix in indexes)


def upgrade() -> None:
    bind = op.get_bind()
    insp = sa.inspect(bind)

    # ---- assignments: late_policy, late_penalty_pct, rubric ----
    if insp.has_table("assignments"):
        if not _has_column(insp, "assignments", "late_policy"):
            op.add_column(
                "assignments",
                sa.Column("late_policy", sa.String(10), nullable=False, server_default="allow"),
            )
        if not _has_column(insp, "assignments", "late_penalty_pct"):
            op.add_column(
                "assignments",
                sa.Column("late_penalty_pct", sa.Integer(), nullable=False, server_default="0"),
            )
        if not _has_column(insp, "assignments", "rubric"):
            op.add_column(
                "assignments",
                sa.Column("rubric", sa.JSON(), nullable=True),
            )
    else:
        print(
            "[0003_learning_experience] assignments table missing entirely — "
            "skipping assignment column additions (unexpected pre-Task-1 state)."
        )

    # ---- assignment_submissions: is_late, rubric_scores, uq_assignment_user ----
    if insp.has_table("assignment_submissions"):
        if not _has_column(insp, "assignment_submissions", "is_late"):
            op.add_column(
                "assignment_submissions",
                sa.Column("is_late", sa.Boolean(), nullable=False, server_default=sa.false()),
            )
        if not _has_column(insp, "assignment_submissions", "rubric_scores"):
            op.add_column(
                "assignment_submissions",
                sa.Column("rubric_scores", sa.JSON(), nullable=True),
            )

        # Re-inspect after any column adds above (some dialects need a fresh
        # inspector to see just-added columns before adding a constraint).
        insp = sa.inspect(bind)
        if not _has_unique_constraint(insp, "assignment_submissions", "uq_assignment_user"):
            try:
                if bind.dialect.name == "sqlite":
                    # SQLite has no ALTER TABLE ADD CONSTRAINT — Alembic's
                    # batch mode does the copy-and-move dance required to
                    # add a UNIQUE constraint after table creation. Without
                    # this, create_unique_constraint raises
                    # NotImplementedError on SQLite and the constraint is
                    # silently never added on a real (non create_all-seeded)
                    # SQLite database.
                    with op.batch_alter_table("assignment_submissions") as batch_op:
                        batch_op.create_unique_constraint(
                            "uq_assignment_user", ["assignment_id", "user_id"]
                        )
                else:
                    op.create_unique_constraint(
                        "uq_assignment_user",
                        "assignment_submissions",
                        ["assignment_id", "user_id"],
                    )
            except Exception as exc:
                # Pre-existing duplicate (assignment_id, user_id) rows would
                # make this fail on a populated table. Don't abort the whole
                # migration for that — surface it loudly so an operator can
                # dedupe and re-run, consistent with this repo's tolerance
                # for partial-apply dual-path startup.
                print(
                    "[0003_learning_experience] could not create "
                    f"uq_assignment_user (likely duplicate rows present): {exc}"
                )
    else:
        print(
            "[0003_learning_experience] assignment_submissions table missing "
            "entirely — skipping submission column additions."
        )

    # ---- h5p_contents (new table) ----
    # Created before lessons.h5p_content_id below since that column's FK
    # references this table.
    if not insp.has_table("h5p_contents"):
        op.create_table(
            "h5p_contents",
            sa.Column("id", sa.Integer(), primary_key=True, index=True),
            sa.Column("public_id", sa.String(32), nullable=False),
            sa.Column("owner_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
            sa.Column("title", sa.String(255), nullable=False),
            sa.Column("library", sa.String(120), nullable=True),
            sa.Column("size_bytes", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("status", sa.String(20), nullable=False, server_default="uploaded"),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
            sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        )
        op.create_index("ix_h5p_contents_public_id", "h5p_contents", ["public_id"], unique=True)
        op.create_index("ix_h5p_contents_owner_id", "h5p_contents", ["owner_id"])
    else:
        print("[0003_learning_experience] h5p_contents already exists — skipping create.")

    # ---- h5p_results (new table) ----
    insp = sa.inspect(bind)  # re-inspect so has_table sees h5p_contents just created
    if not insp.has_table("h5p_results") and insp.has_table("h5p_contents"):
        op.create_table(
            "h5p_results",
            sa.Column("id", sa.Integer(), primary_key=True, index=True),
            sa.Column("content_id", sa.Integer(), sa.ForeignKey("h5p_contents.id"), nullable=False),
            sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
            sa.Column("score", sa.Integer(), nullable=True),
            sa.Column("max_score", sa.Integer(), nullable=True),
            sa.Column("completed", sa.Boolean(), nullable=False, server_default=sa.false()),
            sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
            sa.UniqueConstraint("content_id", "user_id", name="uq_h5p_result_content_user"),
        )
        op.create_index("ix_h5p_results_content_id", "h5p_results", ["content_id"])
        op.create_index("ix_h5p_results_user_id", "h5p_results", ["user_id"])
    elif insp.has_table("h5p_results"):
        print("[0003_learning_experience] h5p_results already exists — skipping create.")
    else:
        print(
            "[0003_learning_experience] h5p_contents missing — skipping "
            "h5p_results create (FK dependency)."
        )

    # ---- lessons: lesson_content_type, h5p_content_id ----
    insp = sa.inspect(bind)
    if insp.has_table("lessons"):
        if not _has_column(insp, "lessons", "lesson_content_type"):
            op.add_column(
                "lessons",
                sa.Column("lesson_content_type", sa.String(20), nullable=True, server_default="video"),
            )
        if not _has_column(insp, "lessons", "h5p_content_id"):
            if insp.has_table("h5p_contents"):
                if bind.dialect.name == "sqlite":
                    # SQLite's ALTER TABLE ADD COLUMN cannot attach a FOREIGN
                    # KEY to an existing table — the plain op.add_column below
                    # raises and aborts the whole upgrade on any real (i.e.
                    # not create_all-seeded) SQLite database. Batch mode does
                    # the copy-and-move dance, mirroring the downgrade's
                    # drop_column block and the uq_assignment_user block above.
                    #
                    # The FK must be NAMED here: batch mode recreates the
                    # table from reflection, and SQLAlchemy refuses to emit an
                    # anonymous constraint in that path ("Constraint must have
                    # a name"). The non-SQLite branch keeps the inline
                    # unnamed ForeignKey it has always used, so no existing
                    # Postgres deployment sees a constraint-name change.
                    with op.batch_alter_table("lessons") as batch_op:
                        batch_op.add_column(
                            sa.Column("h5p_content_id", sa.Integer(), nullable=True)
                        )
                        batch_op.create_foreign_key(
                            "fk_lessons_h5p_content_id",
                            "h5p_contents",
                            ["h5p_content_id"],
                            ["id"],
                        )
                else:
                    op.add_column(
                        "lessons",
                        sa.Column(
                            "h5p_content_id",
                            sa.Integer(),
                            sa.ForeignKey("h5p_contents.id"),
                            nullable=True,
                        ),
                    )
            else:
                print(
                    "[0003_learning_experience] h5p_contents missing — "
                    "skipping lessons.h5p_content_id add (FK dependency)."
                )
    else:
        print("[0003_learning_experience] lessons table missing entirely — skipping H5P lesson columns.")

    # ---- certificates: is_global (Task 6 — designer API) ----
    insp = sa.inspect(bind)
    if insp.has_table("certificates"):
        if not _has_column(insp, "certificates", "is_global"):
            op.add_column(
                "certificates",
                sa.Column("is_global", sa.Boolean(), nullable=False, server_default=sa.false()),
            )
    else:
        print("[0003_learning_experience] certificates table missing entirely — skipping is_global add.")

    # ---- xp_events (Task 9 — new table) ----
    insp = sa.inspect(bind)
    if not insp.has_table("xp_events"):
        op.create_table(
            "xp_events",
            sa.Column("id", sa.Integer(), primary_key=True, index=True),
            sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
            sa.Column("event_key", sa.String(120), nullable=False),
            sa.Column("event_type", sa.String(40), nullable=False),
            sa.Column("points", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("course_id", sa.Integer(), sa.ForeignKey("courses.id"), nullable=True),
            sa.Column("meta", sa.JSON(), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        )
        op.create_index("ix_xp_events_user_id", "xp_events", ["user_id"])
        op.create_index("ix_xp_events_event_key", "xp_events", ["event_key"], unique=True)
        op.create_index("ix_xp_events_event_type", "xp_events", ["event_type"])
        op.create_index("ix_xp_events_course_id", "xp_events", ["course_id"])
    else:
        print("[0003_learning_experience] xp_events already exists — skipping create.")

    # ---- user_game_stats (Task 9 — new table) ----
    insp = sa.inspect(bind)
    if not insp.has_table("user_game_stats"):
        op.create_table(
            "user_game_stats",
            sa.Column("id", sa.Integer(), primary_key=True, index=True),
            sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
            sa.Column("total_xp", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("current_streak", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("longest_streak", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("last_active_date", sa.Date(), nullable=True),
            sa.Column("leaderboard_visible", sa.Boolean(), nullable=False, server_default=sa.true()),
            sa.Column("badges_count", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        )
        op.create_index("ix_user_game_stats_user_id", "user_game_stats", ["user_id"], unique=True)
    else:
        print("[0003_learning_experience] user_game_stats already exists — skipping create.")

    # ---- badges (Task 9 — new table) ----
    insp = sa.inspect(bind)
    if not insp.has_table("badges"):
        op.create_table(
            "badges",
            sa.Column("id", sa.Integer(), primary_key=True, index=True),
            sa.Column("slug", sa.String(60), nullable=False),
            sa.Column("name", sa.String(120), nullable=False),
            sa.Column("description", sa.String(255), nullable=False, server_default=""),
            sa.Column("icon", sa.String(40), nullable=False, server_default="award"),
            sa.Column("rule_type", sa.String(40), nullable=False),
            sa.Column("rule_value", sa.Integer(), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        )
        op.create_index("ix_badges_slug", "badges", ["slug"], unique=True)
    else:
        print("[0003_learning_experience] badges already exists — skipping create.")

    # ---- user_badges (Task 9 — new table) ----
    insp = sa.inspect(bind)
    if not insp.has_table("user_badges") and insp.has_table("badges"):
        op.create_table(
            "user_badges",
            sa.Column("id", sa.Integer(), primary_key=True, index=True),
            sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
            sa.Column("badge_id", sa.Integer(), sa.ForeignKey("badges.id"), nullable=False),
            sa.Column("awarded_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
            sa.UniqueConstraint("user_id", "badge_id", name="uq_user_badge"),
        )
        op.create_index("ix_user_badges_user_id", "user_badges", ["user_id"])
        op.create_index("ix_user_badges_badge_id", "user_badges", ["badge_id"])
    elif insp.has_table("user_badges"):
        print("[0003_learning_experience] user_badges already exists — skipping create.")
    else:
        print(
            "[0003_learning_experience] badges missing — skipping user_badges "
            "create (FK dependency)."
        )


def downgrade() -> None:
    bind = op.get_bind()
    insp = sa.inspect(bind)

    # ---- user_badges / badges / user_game_stats / xp_events (Task 9) ----
    # Drop in FK-dependency order: user_badges (references badges) first.
    if insp.has_table("user_badges"):
        op.drop_table("user_badges")

    insp = sa.inspect(bind)
    if insp.has_table("badges"):
        op.drop_table("badges")

    if insp.has_table("user_game_stats"):
        op.drop_table("user_game_stats")

    if insp.has_table("xp_events"):
        op.drop_table("xp_events")

    insp = sa.inspect(bind)

    # ---- certificates: drop is_global ----
    if insp.has_table("certificates") and _has_column(insp, "certificates", "is_global"):
        op.drop_column("certificates", "is_global")

    # ---- lessons: drop H5P columns first (FK to h5p_contents) ----
    if insp.has_table("lessons"):
        if _has_column(insp, "lessons", "h5p_content_id"):
            if bind.dialect.name == "sqlite":
                # SQLite's ALTER TABLE DROP COLUMN chokes when the column
                # participates in a FOREIGN KEY definition ("unknown column
                # ... in foreign key definition") — batch mode does the
                # copy-and-move dance needed to drop it cleanly, same
                # rationale as the uq_assignment_user batch block above.
                with op.batch_alter_table("lessons") as batch_op:
                    batch_op.drop_column("h5p_content_id")
            else:
                op.drop_column("lessons", "h5p_content_id")
        if _has_column(insp, "lessons", "lesson_content_type"):
            op.drop_column("lessons", "lesson_content_type")

    if insp.has_table("h5p_results"):
        op.drop_table("h5p_results")

    if insp.has_table("h5p_contents"):
        op.drop_table("h5p_contents")

    insp = sa.inspect(bind)
    if insp.has_table("assignment_submissions"):
        if _has_unique_constraint(insp, "assignment_submissions", "uq_assignment_user"):
            try:
                if bind.dialect.name == "sqlite":
                    with op.batch_alter_table("assignment_submissions") as batch_op:
                        batch_op.drop_constraint("uq_assignment_user", type_="unique")
                else:
                    op.drop_constraint(
                        "uq_assignment_user", "assignment_submissions", type_="unique"
                    )
            except Exception as exc:
                print(f"[0003_learning_experience] downgrade: could not drop uq_assignment_user: {exc}")
        if _has_column(insp, "assignment_submissions", "rubric_scores"):
            op.drop_column("assignment_submissions", "rubric_scores")
        if _has_column(insp, "assignment_submissions", "is_late"):
            op.drop_column("assignment_submissions", "is_late")

    if insp.has_table("assignments"):
        if _has_column(insp, "assignments", "rubric"):
            op.drop_column("assignments", "rubric")
        if _has_column(insp, "assignments", "late_penalty_pct"):
            op.drop_column("assignments", "late_penalty_pct")
        if _has_column(insp, "assignments", "late_policy"):
            op.drop_column("assignments", "late_policy")
