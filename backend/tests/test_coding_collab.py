"""Phase 5 (part B): pair rooms, single-use tickets, and the realtime relay."""

import pytest
from starlette.websockets import WebSocketDisconnect

from app.models.coding_collab import CodingCollabMember
from tests.test_coding_analytics import _enrol, _publish
from tests.test_coding_assessments import _course


ROOT = "/api/v1/utporul/coding"
KIND_UPDATE = 0
KIND_SNAPSHOT = 1


def _room(client, db, make_user, as_user):
    instructor, course = _course(db, make_user)
    slug = _publish(client, course, instructor, as_user)
    owner = make_user(role="student")
    _enrol(db, course, owner)
    as_user(owner)
    created = client.post(f"{ROOT}/challenges/{slug}/collab-rooms", json={})
    assert created.status_code == 201, created.text
    return course, slug, owner, created.json()


def _ticket(client, room_id):
    response = client.post(f"{ROOT}/collab-rooms/{room_id}/ticket")
    assert response.status_code == 200, response.text
    return response.json()["ticket"]


def _join_as(client, db, make_user, as_user, course, code):
    partner = make_user(role="student")
    _enrol(db, course, partner)
    as_user(partner)
    joined = client.post(f"{ROOT}/collab-rooms/join", json={"code": code})
    assert joined.status_code == 200, joined.text
    return partner


def test_create_join_and_member_only_access(client, db, make_user, as_user):
    course, slug, owner, room = _room(client, db, make_user, as_user)
    assert room["is_owner"] is True
    assert len(room["invite_code"]) >= 16

    stranger = make_user(role="student")
    _enrol(db, course, stranger)
    as_user(stranger)
    assert client.get(f"{ROOT}/collab-rooms/{room['id']}").status_code == 404
    assert client.post(f"{ROOT}/collab-rooms/{room['id']}/ticket").status_code == 404

    partner = _join_as(client, db, make_user, as_user, course, room["invite_code"])
    as_user(partner)
    detail = client.get(f"{ROOT}/collab-rooms/{room['id']}").json()
    assert [m["user_id"] for m in detail["members"]] == [owner.id, partner.id]
    assert detail["is_owner"] is False

    as_user(stranger)
    bad = client.post(f"{ROOT}/collab-rooms/join", json={"code": "not-a-real-code-000"})
    assert bad.status_code == 404


def test_room_is_capped_at_four_members(client, db, make_user, as_user):
    course, slug, owner, room = _room(client, db, make_user, as_user)
    for _ in range(3):
        _join_as(client, db, make_user, as_user, course, room["invite_code"])
    extra = make_user(role="student")
    _enrol(db, course, extra)
    as_user(extra)
    full = client.post(f"{ROOT}/collab-rooms/join", json={"code": room["invite_code"]})
    assert full.status_code == 409
    assert db.query(CodingCollabMember).filter_by(room_id=room["id"]).count() == 4


def test_socket_requires_a_single_use_ticket(client, db, make_user, as_user):
    _course_obj, _slug, owner, room = _room(client, db, make_user, as_user)
    as_user(owner)
    ticket = _ticket(client, room["id"])
    with client.websocket_connect(f"{ROOT}/collab-rooms/{room['id']}/ws?ticket={ticket}") as ws:
        ws.send_bytes(bytes([KIND_UPDATE]) + b"\x01\x02")
    with pytest.raises(WebSocketDisconnect) as reused:
        with client.websocket_connect(f"{ROOT}/collab-rooms/{room['id']}/ws?ticket={ticket}") as ws:
            ws.receive_bytes()
    assert reused.value.code == 4401

    with pytest.raises(WebSocketDisconnect):
        with client.websocket_connect(f"{ROOT}/collab-rooms/{room['id']}/ws?ticket=forged") as ws:
            ws.receive_bytes()


def test_frames_relay_between_members_and_snapshot_catches_up_late_joiners(
    client, db, make_user, as_user
):
    course, slug, owner, room = _room(client, db, make_user, as_user)
    as_user(owner)
    owner_ticket = _ticket(client, room["id"])
    as_user(owner)
    partner = _join_as(client, db, make_user, as_user, course, room["invite_code"])
    as_user(partner)
    partner_ticket = _ticket(client, room["id"])

    path = f"{ROOT}/collab-rooms/{room['id']}/ws"
    with client.websocket_connect(f"{path}?ticket={owner_ticket}") as a:
        with client.websocket_connect(f"{path}?ticket={partner_ticket}") as b:
            a.send_bytes(bytes([KIND_UPDATE]) + b"hello-from-owner")
            assert b.receive_bytes() == bytes([KIND_UPDATE]) + b"hello-from-owner"
            b.send_bytes(bytes([KIND_SNAPSHOT]) + b"full-state-bytes")
            assert a.receive_bytes() == bytes([KIND_SNAPSHOT]) + b"full-state-bytes"

    as_user(owner)
    late_ticket = _ticket(client, room["id"])
    with client.websocket_connect(f"{path}?ticket={late_ticket}") as late:
        first = late.receive_bytes()
        assert first == bytes([KIND_SNAPSHOT]) + b"full-state-bytes"


def test_malformed_frames_close_the_socket(client, db, make_user, as_user):
    _course_obj, _slug, owner, room = _room(client, db, make_user, as_user)
    as_user(owner)
    ticket = _ticket(client, room["id"])
    with client.websocket_connect(f"{ROOT}/collab-rooms/{room['id']}/ws?ticket={ticket}") as ws:
        ws.send_bytes(bytes([9]) + b"not a kind we know")
        with pytest.raises(WebSocketDisconnect) as closed:
            ws.receive_bytes()
        assert closed.value.code == 1003
