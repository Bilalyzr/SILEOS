"""Demo learning games for the walkthrough. Throwaway.

Creates one PUBLISHED game per template (5 games), owned by
priya@sashademo.com, each with 4-6 realistic learning items, and attaches
the quiz_rush game to course 1 (Full-Stack Web Development Bootcamp) as a
'game' lesson. Idempotent-ish: skips creation when a game with the same
title (or a lesson with the same title) already exists.

Run against a scratch/dev DB, e.g.:
    DATABASE_URL=sqlite:///./scratch_games_demo.db python seed_games_demo.py
(after `alembic upgrade head` or an init_db() pass against that same DB —
see docs/LEARNING_GAMES.md "Ops"). Do NOT point this at a shared/live DB
without checking with whoever owns its demo data first.
"""
import os

os.environ.setdefault("DATABASE_URL", "sqlite:///./visual_qa.db")
os.environ.setdefault("REDIS_URL", "redis://127.0.0.1:6379/0?socket_connect_timeout=0.05")
os.environ.setdefault("SECRET_KEY", "x" * 64)
os.environ.setdefault("JWT_SECRET", "y" * 64)
os.environ.setdefault("VIDEO_SECRET", "visual-qa-secret-0123456789abcdef")
os.environ.setdefault("ENVIRONMENT", "development")

from app.core.database import SessionLocal
from app.models.course import Lesson
from app.models.game import Game
from app.models.user import User
from app.schemas.game_config import validate_game_config

COURSE_ID = 1

# Real learning content, no lorem ipsum. Mixed subjects across templates so
# the demo doesn't read as five variations of the same topic.
DEMO_GAMES = {
    "quiz_rush": ("HTML & CSS Basics Rush", {
        "items": [
            {"prompt": "Which tag creates a hyperlink?",
             "options": ["<a>", "<link>", "<nav>", "<href>"], "answer_index": 0},
            {"prompt": "Which tag embeds an image?",
             "options": ["<image>", "<img>", "<pic>", "<src>"], "answer_index": 1},
            {"prompt": "Where does the page <title> belong?",
             "options": ["<body>", "<head>", "<footer>", "<meta>"], "answer_index": 1},
            {"prompt": "Which CSS property controls text color?",
             "options": ["background", "color", "font-family", "border"], "answer_index": 1},
            {"prompt": "Which CSS property adds space OUTSIDE an element's border?",
             "options": ["padding", "margin", "gap", "outline"], "answer_index": 1},
            {"prompt": "Which HTML element is the top-level container for a document?",
             "options": ["<html>", "<doctype>", "<root>", "<page>"], "answer_index": 0},
        ],
        "settings": {"seconds_per_question": 15, "shuffle": True},
    }),
    "match_pairs": ("Cell Biology: Organelle Match", {
        "items": [
            {"left": "Nucleus", "right": "Stores DNA and controls the cell"},
            {"left": "Mitochondrion", "right": "Produces ATP through respiration"},
            {"left": "Ribosome", "right": "Synthesizes proteins"},
            {"left": "Golgi apparatus", "right": "Packages and ships proteins"},
            {"left": "Lysosome", "right": "Breaks down waste with enzymes"},
            {"left": "Chloroplast", "right": "Captures light for photosynthesis"},
        ],
        "settings": {"time_limit_s": 0},
    }),
    "drag_sort": ("Frontend vs Backend Technologies", {
        "categories": [{"name": "Frontend"}, {"name": "Backend"}],
        "items": [
            {"text": "React", "category_index": 0},
            {"text": "Tailwind CSS", "category_index": 0},
            {"text": "Vite", "category_index": 0},
            {"text": "FastAPI", "category_index": 1},
            {"text": "PostgreSQL", "category_index": 1},
            {"text": "SQLAlchemy", "category_index": 1},
        ],
        "settings": {"time_limit_s": 120},
    }),
    "word_builder": ("Spell the Web Dev Keyword", {
        "items": [
            {"clue": "Python web framework used by this LMS backend", "answer": "fastapi"},
            {"clue": "Programming language that runs in every browser", "answer": "javascript"},
            {"clue": "CSS layout system for aligning items in rows or columns", "answer": "flexbox"},
            {"clue": "The relational database used in production here", "answer": "postgresql"},
        ],
        "settings": {"hints_allowed": 2},
    }),
    "sequence": ("HTTP Request Lifecycle", {
        "items": [
            {"text": "Browser resolves the domain name via DNS"},
            {"text": "Browser opens a TCP/TLS connection to the server"},
            {"text": "Browser sends the HTTP request"},
            {"text": "Server routes the request to a handler"},
            {"text": "Handler queries the database if needed"},
            {"text": "Server sends back the HTTP response"},
        ],
        "settings": {"time_limit_s": 0, "shuffle": True},
    }),
}


def main():
    db = SessionLocal()
    instructor = db.query(User).filter(User.user_email == "priya@sashademo.com").first()
    if not instructor:
        print("priya@sashademo.com not found — run the demo user seed first.")
        return

    games_by_template = {}
    for template, (title, config) in DEMO_GAMES.items():
        validate_game_config(template, config)  # fail loudly on drift from the schemas
        game = db.query(Game).filter(Game.title == title).first()
        if not game:
            game = Game(owner_id=instructor.id, title=title, template=template,
                        config=config, status="published")
            db.add(game)
            db.commit()
            db.refresh(game)
            print(f"game created: {template} -> {game.id} ({title})")
        else:
            print(f"game exists: {template} -> {game.id} ({title})")
        games_by_template[template] = game

    lesson_title = "Play: HTML & CSS Basics Rush"
    lesson = db.query(Lesson).filter(
        Lesson.post_parent == COURSE_ID, Lesson.post_title == lesson_title).first()
    if not lesson:
        lesson = Lesson(
            post_author=instructor.id,
            post_parent=COURSE_ID,
            post_title=lesson_title,
            post_content="",
            lesson_content_type="game",
            game_id=games_by_template["quiz_rush"].id,
        )
        db.add(lesson)
        db.commit()
        print(f"game lesson created on course {COURSE_ID}: {lesson.id}")
    else:
        print(f"game lesson exists: {lesson.id}")

    print()
    print("Summary:")
    for template, game in games_by_template.items():
        item_count = len((game.config or {}).get("items") or [])
        print(f"  - {template}: '{game.title}' (id={game.id}, status={game.status}, "
              f"items={item_count}, max_score={item_count * 10})")
    print(f"  - lesson '{lesson_title}' on course {COURSE_ID} (id={lesson.id}) -> "
          f"game {games_by_template['quiz_rush'].id}")


if __name__ == "__main__":
    main()
