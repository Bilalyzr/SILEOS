"""money operations — refund intent columns on payments, admin-processing
columns on withdrawals

MERGE WARNING: the `digital-library` branch ALSO introduces a revision off
0004 (its file is 0005_digital_library.py). This revision deliberately uses
the id "0005m" so the two ids never collide, but the graph will have TWO
heads after both branches land — whoever merges second must add an Alembic
merge revision (`alembic merge -m "merge money-ops + digital-library"
0005m <other-id>`) or re-chain one of the two down_revisions before running
`alembic upgrade head`.

Guarded like 0002/0003/0004: init_db()'s create_all may already have created
these columns via the SQLAlchemy models before Alembic runs, so every
operation checks _has_column first. The two FK columns
(payments.refund_requested_by, withdrawals.processed_by) use
batch_alter_table on SQLite — ALTER TABLE ADD COLUMN cannot attach an FK
there, and the FK must be NAMED in the batch path (same dance as 0004's
lessons.game_id block).

Revision ID: 0005m
Revises: 0004
Create Date: 2026-09-04
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "0005m"
down_revision: Union[str, None] = "0004"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _has_column(insp, table_name: str, column_name: str) -> bool:
    if not insp.has_table(table_name):
        return False
    return any(col["name"] == column_name for col in insp.get_columns(table_name))


# (table, column) -> plain (non-FK) column factory
_PLAIN_COLUMNS = [
    ("payments", "refund_status", lambda: sa.Column("refund_status", sa.String(20), nullable=True)),
    ("payments", "refund_reason", lambda: sa.Column("refund_reason", sa.Text(), nullable=True)),
    ("payments", "refund_requested_at", lambda: sa.Column("refund_requested_at", sa.DateTime(timezone=True), nullable=True)),
    ("payments", "refund_processed_at", lambda: sa.Column("refund_processed_at", sa.DateTime(timezone=True), nullable=True)),
    ("payments", "refund_error", lambda: sa.Column("refund_error", sa.Text(), nullable=True)),
    ("payments", "gateway_refund_id", lambda: sa.Column("gateway_refund_id", sa.String(255), nullable=True)),
    ("withdrawals", "paid_reference", lambda: sa.Column("paid_reference", sa.String(255), nullable=True, server_default="")),
    ("withdrawals", "processed_at", lambda: sa.Column("processed_at", sa.DateTime(timezone=True), nullable=True)),
]

# (table, column, fk_name) -> FK to users.id
_FK_COLUMNS = [
    ("payments", "refund_requested_by", "fk_payments_refund_requested_by_users"),
    ("withdrawals", "processed_by", "fk_withdrawals_processed_by_users"),
]


def upgrade() -> None:
    bind = op.get_bind()
    insp = sa.inspect(bind)

    for table, column, factory in _PLAIN_COLUMNS:
        if not insp.has_table(table):
            print(f"[0005_money_ops] {table} missing — skipping {column} add.")
            continue
        if _has_column(insp, table, column):
            print(f"[0005_money_ops] {table}.{column} already exists — skipping.")
            continue
        op.add_column(table, factory())

    insp = sa.inspect(bind)
    for table, column, fk_name in _FK_COLUMNS:
        if not insp.has_table(table) or not insp.has_table("users"):
            print(f"[0005_money_ops] {table}/users missing — skipping {column} add (FK dependency).")
            continue
        if _has_column(insp, table, column):
            print(f"[0005_money_ops] {table}.{column} already exists — skipping.")
            continue
        if bind.dialect.name == "sqlite":
            with op.batch_alter_table(table) as batch_op:
                batch_op.add_column(sa.Column(column, sa.Integer(), nullable=True))
                batch_op.create_foreign_key(fk_name, "users", [column], ["id"])
        else:
            op.add_column(
                table,
                sa.Column(column, sa.Integer(), sa.ForeignKey("users.id"), nullable=True),
            )

    insp = sa.inspect(bind)
    if insp.has_table("payments") and _has_column(insp, "payments", "refund_status"):
        existing = {ix["name"] for ix in insp.get_indexes("payments")}
        if "ix_payments_refund_status" not in existing:
            op.create_index("ix_payments_refund_status", "payments", ["refund_status"])


def downgrade() -> None:
    bind = op.get_bind()
    insp = sa.inspect(bind)

    if insp.has_table("payments"):
        existing = {ix["name"] for ix in insp.get_indexes("payments")}
        if "ix_payments_refund_status" in existing:
            op.drop_index("ix_payments_refund_status", table_name="payments")

    # FK columns first (reverse of upgrade), batch mode on SQLite.
    for table, column, _fk_name in reversed(_FK_COLUMNS):
        insp = sa.inspect(bind)
        if insp.has_table(table) and _has_column(insp, table, column):
            if bind.dialect.name == "sqlite":
                with op.batch_alter_table(table) as batch_op:
                    batch_op.drop_column(column)
            else:
                op.drop_column(table, column)

    for table, column, _factory in reversed(_PLAIN_COLUMNS):
        insp = sa.inspect(bind)
        if insp.has_table(table) and _has_column(insp, table, column):
            if bind.dialect.name == "sqlite":
                with op.batch_alter_table(table) as batch_op:
                    batch_op.drop_column(column)
            else:
                op.drop_column(table, column)
