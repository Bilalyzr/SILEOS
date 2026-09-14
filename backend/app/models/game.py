"""Learning-game models (spec 2026-09-03-learning-games §2).

`Game` is one instructor-authored game: a `template` key (one of the 5
launch templates) + the JSON `config` that drives the client-side engine.
`max_score` is NEVER stored — it is derived server-side as 10 x item count
(app/schemas/game_config.derive_max_score) everywhere it is needed.

`GameResult` records one advisory play attempt. Multiple attempts are kept
(no unique constraint); "best score" is computed in queries. Per the spec's
security model these scores are advisory engagement data (grading happens
client-side for instant feedback), NEVER gradebook truth — identical
posture to app/models/h5p.H5PResult.
"""
from sqlalchemy import JSON, Boolean, Column, DateTime, ForeignKey, Integer, String
from sqlalchemy.sql import func

from app.core.database import Base


class Game(Base):
    """One instructor-authored learning game (template + config)."""
    __tablename__ = "games"

    id = Column(Integer, primary_key=True, index=True)
    owner_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)

    title = Column(String(200), nullable=False)
    # One of: quiz_rush | match_pairs | drag_sort | word_builder | sequence
    # (validated by app/schemas/game_config.py — enum enforced at the API
    # layer, not as a DB CHECK, matching lesson_content_type's precedent).
    template = Column(String(32), nullable=False)
    # Marketplace v1: publicly listed games any instructor can insert.
    is_listed = Column(Boolean, default=False)
    config = Column(JSON, nullable=False)

    # draft (owner-only) -> published (attachable + playable). Unpublish is
    # blocked with 409 while any lesson references the game.
    status = Column(String(16), nullable=False, default="draft")

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    def __repr__(self):
        return f"<Game(id={self.id}, template={self.template}, status={self.status})>"


class GameResult(Base):
    """One advisory play attempt. Multiple rows per (game, user) by design."""
    __tablename__ = "game_results"

    id = Column(Integer, primary_key=True, index=True)
    game_id = Column(Integer, ForeignKey("games.id"), nullable=False, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)

    score = Column(Integer, nullable=False)
    max_score = Column(Integer, nullable=False)
    duration_s = Column(Integer, nullable=False, default=0)

    created_at = Column(DateTime(timezone=True), server_default=func.now())

    def __repr__(self):
        return f"<GameResult(game_id={self.game_id}, user_id={self.user_id}, score={self.score}/{self.max_score})>"
