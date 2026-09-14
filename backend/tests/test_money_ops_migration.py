"""Money Operations migration + model columns
(docs/superpowers/specs/2026-09-04-money-ops-design.md §1.3, §4).

Mirrors tests/test_games.py::TestMigration0004 — run the revision's upgrade()
against a scratch SQLite FILE db that already has the FK-target tables, then
inspect. Model tests use the shared in-memory `db` fixture.
"""
import importlib.util
from pathlib import Path

import sqlalchemy as sa
from alembic.migration import MigrationContext
from alembic.operations import Operations

from app.models.payment import Order, OrderStatus, Payment, PaymentStatus, Withdrawal


def _load_migration():
    path = Path(__file__).resolve().parents[1] / "alembic" / "versions" / "0005_money_ops.py"
    spec = importlib.util.spec_from_file_location("mig_0005m", path)
    mig = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mig)
    return mig


def _bare_engine(tmp_path):
    engine = sa.create_engine(f"sqlite:///{tmp_path / 'mig.db'}")
    with engine.begin() as conn:
        conn.execute(sa.text("CREATE TABLE users (id INTEGER PRIMARY KEY)"))
        conn.execute(sa.text("CREATE TABLE orders (id INTEGER PRIMARY KEY)"))
        conn.execute(sa.text(
            "CREATE TABLE payments (id INTEGER PRIMARY KEY, order_id INTEGER, "
            "user_id INTEGER, payment_method VARCHAR(50), amount NUMERIC(13,4))"))
        conn.execute(sa.text(
            "CREATE TABLE withdrawals (withdraw_id INTEGER PRIMARY KEY, user_id INTEGER, "
            "amount NUMERIC(16,2), status VARCHAR(50))"))
    return engine


def _run(engine, fn):
    with engine.connect() as conn:
        ctx = MigrationContext.configure(conn)
        with Operations.context(ctx):
            fn()
        conn.commit()


class TestMigration0005m:
    def test_revision_ids(self):
        mig = _load_migration()
        assert mig.revision == "0005m"
        assert mig.down_revision == "0004"

    def test_upgrade_adds_columns(self, tmp_path):
        mig = _load_migration()
        engine = _bare_engine(tmp_path)
        _run(engine, mig.upgrade)
        insp = sa.inspect(engine)
        pay_cols = {c["name"] for c in insp.get_columns("payments")}
        assert {"refund_status", "refund_reason", "refund_requested_by",
                "refund_requested_at", "refund_processed_at", "refund_error",
                "gateway_refund_id"} <= pay_cols
        wd_cols = {c["name"] for c in insp.get_columns("withdrawals")}
        assert {"paid_reference", "processed_by", "processed_at"} <= wd_cols

    def test_upgrade_creates_users_fks_and_refund_status_index(self, tmp_path):
        """The two new users.id FK columns must actually carry FKs (they are
        added through batch_alter_table with NAMED constraints on SQLite), and
        the refund_status index the payment-health queries rely on must exist."""
        mig = _load_migration()
        engine = _bare_engine(tmp_path)
        _run(engine, mig.upgrade)
        insp = sa.inspect(engine)

        def _fk_targets(table, column):
            targets = set()
            for fk in insp.get_foreign_keys(table):
                if column in (fk.get("constrained_columns") or []):
                    targets.add(fk.get("referred_table"))
            return targets

        assert "users" in _fk_targets("payments", "refund_requested_by")
        assert "users" in _fk_targets("withdrawals", "processed_by")
        # (the scratch fixture creates payments/withdrawals with bare INTEGER
        # user_id columns and no FK, so there is no pre-existing FK here to
        # assert survives the batch rebuild.)

        idx = {i["name"] for i in insp.get_indexes("payments")}
        assert "ix_payments_refund_status" in idx

    def test_upgrade_is_rerunnable(self, tmp_path):
        mig = _load_migration()
        engine = _bare_engine(tmp_path)
        _run(engine, mig.upgrade)
        _run(engine, mig.upgrade)  # guarded: second run is a no-op, not an error
        insp = sa.inspect(engine)
        assert "refund_status" in {c["name"] for c in insp.get_columns("payments")}

    def test_downgrade_removes_columns(self, tmp_path):
        mig = _load_migration()
        engine = _bare_engine(tmp_path)
        _run(engine, mig.upgrade)
        _run(engine, mig.downgrade)
        insp = sa.inspect(engine)
        pay_cols = {c["name"] for c in insp.get_columns("payments")}
        assert "refund_status" not in pay_cols and "gateway_refund_id" not in pay_cols
        wd_cols = {c["name"] for c in insp.get_columns("withdrawals")}
        assert "paid_reference" not in wd_cols and "processed_by" not in wd_cols
        # the index goes with the column it indexed
        assert "ix_payments_refund_status" not in {i["name"] for i in insp.get_indexes("payments")}
        # ...and the FKs added alongside the dropped columns are gone with them
        def _fk_targets(table, column):
            return {fk.get("referred_table") for fk in insp.get_foreign_keys(table)
                    if column in (fk.get("constrained_columns") or [])}

        assert _fk_targets("payments", "refund_requested_by") == set()
        assert _fk_targets("withdrawals", "processed_by") == set()


class TestMoneyOpsModelColumns:
    def test_payment_refund_columns_default_null(self, db, student_user):
        order = Order(user_id=student_user.id, order_key="RZP_M1",
                      order_status=OrderStatus.COMPLETED, total_amount=500)
        db.add(order)
        db.flush()
        p = Payment(user_id=student_user.id, order_id=order.id, payment_method="razorpay",
                    gateway_payment_id="pay_M1", amount=500,
                    payment_status=PaymentStatus.COMPLETED)
        db.add(p)
        db.commit()
        db.refresh(p)
        assert p.refund_status is None
        assert p.refund_reason is None
        assert p.refund_requested_by is None
        assert p.gateway_refund_id is None
        assert p.refund_error is None

    def test_withdrawal_admin_columns(self, db, make_user):
        inst = make_user(role="instructor")
        admin = make_user(role="admin")
        w = Withdrawal(user_id=inst.id, amount=750.00,
                       method_data={"type": "upi", "upi_id": "x@upi"})
        db.add(w)
        db.commit()
        db.refresh(w)
        assert w.status == "pending"
        assert w.paid_reference == ""
        assert w.processed_by is None and w.processed_at is None
        w.processed_by = admin.id
        db.commit()
        assert "method_data" not in repr(w)  # never rendered by repr (Global Constraint 5)

    def test_min_withdrawal_setting_default(self):
        from app.core.config import get_settings
        assert get_settings().MIN_WITHDRAWAL_INR == 500
