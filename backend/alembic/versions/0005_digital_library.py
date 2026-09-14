"""digital library — ebooks, ebook_grants, orders.ebook_id,
order_items.ebook_id, order_items.course_id -> nullable

Guarded like 0002/0003/0004: init_db()'s create_all may already have created
these tables/columns via the SQLAlchemy models before Alembic runs, so every
operation checks has_table/_has_column first. FK column adds on SQLite use
batch_alter_table (ADD COLUMN can't attach an FK there — the FK must be
NAMED in the batch path), and the course_id nullability relax also needs
batch mode on SQLite (ALTER COLUMN is unsupported).

Revision ID: 0005
Revises: 0004
Create Date: 2026-09-03
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "0005"
down_revision: Union[str, None] = "0004"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _has_column(insp, table_name: str, column_name: str) -> bool:
    if not insp.has_table(table_name):
        return False
    return any(col["name"] == column_name for col in insp.get_columns(table_name))


def _course_id_nullable(insp) -> bool:
    for col in insp.get_columns("order_items"):
        if col["name"] == "course_id":
            return bool(col["nullable"])
    return True


def upgrade() -> None:
    bind = op.get_bind()
    insp = sa.inspect(bind)

    # ---- ebooks (new table) ----
    if not insp.has_table("ebooks"):
        op.create_table(
            "ebooks",
            sa.Column("id", sa.Integer(), primary_key=True, index=True),
            sa.Column("owner_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
            sa.Column("title", sa.String(200), nullable=False),
            sa.Column("slug", sa.String(255), nullable=False, unique=True),
            sa.Column("description", sa.Text(), server_default=""),
            sa.Column("category", sa.String(16), nullable=False),
            sa.Column("price_inr", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("discount_price_inr", sa.Integer(), nullable=True),
            sa.Column("cover_image", sa.String(500), server_default=""),
            sa.Column("file_path", sa.String(500), nullable=True),
            sa.Column("file_size_bytes", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("page_count", sa.Integer(), nullable=True),
            sa.Column("sample_path", sa.String(500), nullable=True),
            sa.Column("concept_tags", sa.JSON(), nullable=False, server_default="[]"),
            sa.Column("course_id", sa.Integer(), sa.ForeignKey("courses.id"), nullable=True),
            sa.Column("status", sa.String(16), nullable=False, server_default="draft"),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
            sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        )
        op.create_index("ix_ebooks_owner_id", "ebooks", ["owner_id"])
        op.create_index("ix_ebooks_slug", "ebooks", ["slug"])
        op.create_index("ix_ebooks_course_id", "ebooks", ["course_id"])
    else:
        print("[0005_digital_library] ebooks already exists — skipping create.")

    # ---- ebook_grants (new table) ----
    insp = sa.inspect(bind)
    if not insp.has_table("ebook_grants") and insp.has_table("ebooks"):
        op.create_table(
            "ebook_grants",
            sa.Column("id", sa.Integer(), primary_key=True, index=True),
            sa.Column("ebook_id", sa.Integer(), sa.ForeignKey("ebooks.id"), nullable=False),
            sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
            sa.Column("order_id", sa.Integer(), sa.ForeignKey("orders.id"), nullable=True),
            sa.Column("source", sa.String(16), nullable=False, server_default="purchase"),
            sa.Column("granted_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
            sa.UniqueConstraint("ebook_id", "user_id", name="uq_ebook_grants_ebook_user"),
        )
        op.create_index("ix_ebook_grants_ebook_id", "ebook_grants", ["ebook_id"])
        op.create_index("ix_ebook_grants_user_id", "ebook_grants", ["user_id"])
    elif insp.has_table("ebook_grants"):
        print("[0005_digital_library] ebook_grants already exists — skipping create.")
    else:
        print("[0005_digital_library] ebooks missing — skipping ebook_grants create (FK dependency).")

    # ---- orders.ebook_id ----
    insp = sa.inspect(bind)
    if insp.has_table("orders") and insp.has_table("ebooks") \
            and not _has_column(insp, "orders", "ebook_id"):
        if bind.dialect.name == "sqlite":
            with op.batch_alter_table("orders") as batch_op:
                batch_op.add_column(sa.Column("ebook_id", sa.Integer(), nullable=True))
                batch_op.create_foreign_key("fk_orders_ebook_id", "ebooks", ["ebook_id"], ["id"])
        else:
            op.add_column("orders", sa.Column("ebook_id", sa.Integer(),
                                              sa.ForeignKey("ebooks.id"), nullable=True))
        op.create_index("ix_orders_ebook_id", "orders", ["ebook_id"])

    # ---- order_items.ebook_id + course_id nullability relax ----
    insp = sa.inspect(bind)
    if insp.has_table("order_items"):
        add_ebook_id = insp.has_table("ebooks") and not _has_column(insp, "order_items", "ebook_id")
        relax_course_id = not _course_id_nullable(insp)
        if bind.dialect.name == "sqlite":
            if add_ebook_id or relax_course_id:
                with op.batch_alter_table("order_items") as batch_op:
                    if add_ebook_id:
                        batch_op.add_column(sa.Column("ebook_id", sa.Integer(), nullable=True))
                        batch_op.create_foreign_key(
                            "fk_order_items_ebook_id", "ebooks", ["ebook_id"], ["id"])
                    if relax_course_id:
                        batch_op.alter_column("course_id", existing_type=sa.Integer(),
                                              nullable=True)
        else:
            if add_ebook_id:
                op.add_column("order_items", sa.Column("ebook_id", sa.Integer(),
                                                       sa.ForeignKey("ebooks.id"), nullable=True))
            if relax_course_id:
                op.alter_column("order_items", "course_id",
                                existing_type=sa.Integer(), nullable=True)
        if add_ebook_id:
            op.create_index("ix_order_items_ebook_id", "order_items", ["ebook_id"])


def downgrade() -> None:
    bind = op.get_bind()
    insp = sa.inspect(bind)

    # Reverse order: drop FK columns first, then the tables they reference.
    # course_id is deliberately NOT restored to NOT NULL — ebook order rows
    # with course_id NULL may exist and a data-destroying downgrade is worse
    # than a laxer column. The index on each dropped column must be dropped
    # explicitly INSIDE the batch block first — SQLite batch mode's table
    # "recreate" otherwise tries to re-create every index it finds on the
    # reflected table (including this one) against the new table, which no
    # longer has the column and raises "no such column".
    if insp.has_table("order_items") and _has_column(insp, "order_items", "ebook_id"):
        with op.batch_alter_table("order_items") as batch_op:
            batch_op.drop_index("ix_order_items_ebook_id")
            batch_op.drop_column("ebook_id")
    insp = sa.inspect(bind)
    if insp.has_table("orders") and _has_column(insp, "orders", "ebook_id"):
        with op.batch_alter_table("orders") as batch_op:
            batch_op.drop_index("ix_orders_ebook_id")
            batch_op.drop_column("ebook_id")
    insp = sa.inspect(bind)
    if insp.has_table("ebook_grants"):
        op.drop_table("ebook_grants")
    if insp.has_table("ebooks"):
        op.drop_table("ebooks")
