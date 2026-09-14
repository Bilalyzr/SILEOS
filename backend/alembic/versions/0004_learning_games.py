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
