import logging
import threading
import time

from app.models.campus_pilot import CampusWhatsAppMessage
from app.models.whatsapp import WhatsAppMessage
from app.services import campus_whatsapp


def _stub_due_queues(
    monkeypatch,
    TestingSessionLocal,
    *,
    campus_ids=(),
    global_ids=(),
):
    requested = []

    def due_ids(_db, model, _now, _stale_before, limit):
        requested.append((model, limit))
        ids = campus_ids if model is CampusWhatsAppMessage else global_ids
        return list(ids[:limit])

    monkeypatch.setattr(campus_whatsapp, "SessionLocal", TestingSessionLocal)
    monkeypatch.setattr(
        campus_whatsapp,
        "reconcile_status_receipts",
        lambda *_args, **_kwargs: None,
    )
    monkeypatch.setattr(campus_whatsapp, "_due_message_ids", due_ids)
    return requested


def test_delivery_tick_interleaves_queues_and_honors_total_limit(
    monkeypatch, TestingSessionLocal
):
    requested = _stub_due_queues(
        monkeypatch,
        TestingSessionLocal,
        campus_ids=tuple(range(1, 11)),
        global_ids=tuple(range(101, 111)),
    )
    selected = []
    monkeypatch.setattr(
        campus_whatsapp,
        "deliver",
        lambda message_id: selected.append(("campus", message_id)),
    )
    monkeypatch.setattr(
        campus_whatsapp,
        "deliver_global",
        lambda message_id: selected.append(("global", message_id)),
    )

    campus_whatsapp.deliver_pending(limit=5)

    assert requested == [
        (CampusWhatsAppMessage, 5),
        (WhatsAppMessage, 5),
    ]
    assert selected == [
        ("campus", 1),
        ("global", 101),
        ("campus", 2),
        ("global", 102),
        ("campus", 3),
    ]


def test_delivery_tick_caps_concurrency_and_isolates_job_errors(
    monkeypatch, TestingSessionLocal, caplog
):
    _stub_due_queues(
        monkeypatch,
        TestingSessionLocal,
        campus_ids=tuple(range(1, 9)),
    )
    monkeypatch.setattr(campus_whatsapp, "_session_uses_sqlite", lambda _db: False)

    state_lock = threading.Lock()
    four_active = threading.Event()
    release_jobs = threading.Event()
    started = []
    active = 0
    peak = 0

    def delivery(message_id):
        nonlocal active, peak
        with state_lock:
            started.append(message_id)
            active += 1
            peak = max(peak, active)
            if active == campus_whatsapp.DELIVERY_CONCURRENCY:
                four_active.set()
        try:
            release_jobs.wait(timeout=5)
        finally:
            with state_lock:
                active -= 1
        if message_id == 2:
            raise RuntimeError("isolated delivery failure")

    monkeypatch.setattr(campus_whatsapp, "deliver", delivery)
    errors = []

    def run_tick():
        try:
            campus_whatsapp.deliver_pending(limit=8, max_workers=99)
        except BaseException as exc:  # pragma: no cover - asserted below
            errors.append(exc)

    tick = threading.Thread(target=run_tick)
    with caplog.at_level(logging.ERROR, logger=campus_whatsapp.__name__):
        tick.start()
        try:
            assert four_active.wait(timeout=5)
            with state_lock:
                assert len(started) == campus_whatsapp.DELIVERY_CONCURRENCY
                assert peak == campus_whatsapp.DELIVERY_CONCURRENCY
        finally:
            release_jobs.set()
        tick.join(timeout=5)

    assert not tick.is_alive()
    assert errors == []
    assert sorted(started) == list(range(1, 9))
    assert any(
        record.getMessage() == "WhatsApp campus delivery job failed for message 2"
        for record in caplog.records
    )


def test_delivery_tick_uses_one_worker_for_sqlite(monkeypatch, TestingSessionLocal):
    _stub_due_queues(
        monkeypatch,
        TestingSessionLocal,
        campus_ids=(1, 2, 3),
        global_ids=(101, 102, 103),
    )

    state_lock = threading.Lock()
    first_started = threading.Event()
    release_jobs = threading.Event()
    started = []
    active = 0
    peak = 0

    def delivery(queue, message_id):
        nonlocal active, peak
        with state_lock:
            started.append((queue, message_id))
            active += 1
            peak = max(peak, active)
            first_started.set()
        try:
            release_jobs.wait(timeout=5)
        finally:
            with state_lock:
                active -= 1

    monkeypatch.setattr(
        campus_whatsapp,
        "deliver",
        lambda message_id: delivery("campus", message_id),
    )
    monkeypatch.setattr(
        campus_whatsapp,
        "deliver_global",
        lambda message_id: delivery("global", message_id),
    )

    tick = threading.Thread(
        target=lambda: campus_whatsapp.deliver_pending(limit=6, max_workers=4)
    )
    tick.start()
    try:
        assert first_started.wait(timeout=5)
        time.sleep(0.1)
        with state_lock:
            assert active == 1
            assert peak == 1
    finally:
        release_jobs.set()
    tick.join(timeout=5)

    assert not tick.is_alive()
    assert started == [
        ("campus", 1),
        ("global", 101),
        ("campus", 2),
        ("global", 102),
        ("campus", 3),
        ("global", 103),
    ]


def test_overlapping_delivery_tick_is_skipped(monkeypatch, TestingSessionLocal):
    _stub_due_queues(
        monkeypatch,
        TestingSessionLocal,
        campus_ids=(1,),
    )
    first_started = threading.Event()
    release_first = threading.Event()
    calls = []

    def delivery(message_id):
        calls.append(message_id)
        first_started.set()
        release_first.wait(timeout=5)

    monkeypatch.setattr(campus_whatsapp, "deliver", delivery)
    first_tick = threading.Thread(target=campus_whatsapp.deliver_pending)
    second_done = threading.Event()

    def run_second_tick():
        campus_whatsapp.deliver_pending()
        second_done.set()

    second_tick = threading.Thread(target=run_second_tick)
    first_tick.start()
    try:
        assert first_started.wait(timeout=5)
        second_tick.start()
        assert second_done.wait(timeout=1)
        assert calls == [1]
    finally:
        release_first.set()
    first_tick.join(timeout=5)
    second_tick.join(timeout=5)

    assert not first_tick.is_alive()
    assert not second_tick.is_alive()
