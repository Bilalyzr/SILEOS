from app.models.webhook_event import WebhookEvent, WebhookEventStatus


def test_webhook_event_roundtrip(db):
    ev = WebhookEvent(
        event_id="evt_123",
        event_type="payment.captured",
        payload={"a": 1},
        signature_valid=True,
    )
    db.add(ev)
    db.commit()
    db.refresh(ev)
    assert ev.status == WebhookEventStatus.RECEIVED
    assert ev.attempts == 0
    assert ev.received_at is not None


def test_event_id_unique(db):
    db.add(WebhookEvent(event_id="evt_dup", event_type="x", payload={}, signature_valid=True))
    db.commit()
    db.add(WebhookEvent(event_id="evt_dup", event_type="x", payload={}, signature_valid=True))
    import pytest as _pytest
    from sqlalchemy.exc import IntegrityError
    with _pytest.raises(IntegrityError):
        db.commit()
    db.rollback()
