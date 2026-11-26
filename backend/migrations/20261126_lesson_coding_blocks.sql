-- Phase 2 of the coding platform: practice blocks in lessons and learner drafts.
-- Applied automatically at backend start by create_all. This file documents the
-- schema and can be run by hand on a database that already exists.

CREATE TABLE IF NOT EXISTS lesson_coding_blocks (
    id SERIAL PRIMARY KEY,
    lesson_id INTEGER NOT NULL REFERENCES lessons(id) ON DELETE CASCADE,
    challenge_id INTEGER NOT NULL REFERENCES coding_challenges(id) ON DELETE CASCADE,
    position_seconds INTEGER NULL,
    instructions TEXT NOT NULL DEFAULT '',
    ordinal INTEGER NOT NULL DEFAULT 0,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT ck_lesson_coding_block_position CHECK (position_seconds IS NULL OR position_seconds >= 0),
    CONSTRAINT uq_lesson_coding_block UNIQUE (lesson_id, challenge_id, position_seconds)
);
CREATE INDEX IF NOT EXISTS ix_lesson_coding_blocks_lesson_id ON lesson_coding_blocks (lesson_id);
CREATE INDEX IF NOT EXISTS ix_lesson_coding_blocks_challenge_id ON lesson_coding_blocks (challenge_id);

CREATE TABLE IF NOT EXISTS coding_drafts (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    challenge_id INTEGER NOT NULL REFERENCES coding_challenges(id) ON DELETE CASCADE,
    language VARCHAR(30) NOT NULL,
    source_code TEXT NOT NULL DEFAULT '',
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT uq_coding_draft UNIQUE (user_id, challenge_id, language)
);
CREATE INDEX IF NOT EXISTS ix_coding_drafts_user_id ON coding_drafts (user_id);
CREATE INDEX IF NOT EXISTS ix_coding_drafts_challenge_id ON coding_drafts (challenge_id);
