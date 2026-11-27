"""Phase 5 (part B): pair coding rooms.

A room is a shared Yjs document for one challenge. Membership is stored here;
the live document snapshot and the connection tickets live in Redis (see
app/services/coding_collab_service.py).
"""

from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.sql import func

from app.core.database import Base


class CodingCollabRoom(Base):
    __tablename__ = "coding_collab_rooms"

    id = Column(Integer, primary_key=True, index=True)
    challenge_id = Column(
        Integer, ForeignKey("coding_challenges.id", ondelete="CASCADE"), nullable=False, index=True
    )
    owner_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    language = Column(String(30), nullable=False)
    invite_code = Column(String(24), nullable=False, unique=True, index=True)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())

    def __repr__(self):
        return f"<CodingCollabRoom(id={self.id}, challenge_id={self.challenge_id})>"


class CodingCollabMember(Base):
    __tablename__ = "coding_collab_members"

    id = Column(Integer, primary_key=True, index=True)
    room_id = Column(
        Integer, ForeignKey("coding_collab_rooms.id", ondelete="CASCADE"), nullable=False, index=True
    )
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    joined_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())

    __table_args__ = (UniqueConstraint("room_id", "user_id", name="uq_coding_collab_members_room_user"),)

    def __repr__(self):
        return f"<CodingCollabMember(room_id={self.room_id}, user_id={self.user_id})>"
