"""
One-off seeder: build catalog courses from the Bunny Stream library.

Fetches ready (status==4) videos, groups them into 3 courses, dedups repeated
uploads (keeps the longest = most complete copy per logical lesson), orders the
lessons, and inserts courses + lessons wired to Bunny HLS playback URLs.

Idempotent-ish: skips creating a course whose exact title already exists.
Run:  docker compose exec backend python seed_bunny_courses.py
"""
import os, re, httpx, psycopg2
from app.core.security import get_password_hash

DB = os.getenv("DATABASE_URL")
LIB = os.getenv("BUNNY_LIBRARY_ID")
KEY = os.getenv("BUNNY_API_KEY")
HOST = os.getenv("BUNNY_CDN_HOSTNAME")

INSTRUCTOR_EMAIL = "sasha@sashainfinity.com"
INSTRUCTOR_PASS = "Sasha@123"

def hls(g):     return f"https://{HOST}/{g}/playlist.m3u8"
def poster(g):  return f"https://{HOST}/{g}/thumbnail.jpg"
def dur(s):     return str(int(s or 0))  # backend stores lesson_video_duration as seconds-string

def clean(t):
    t = re.sub(r"\.(mp4|m4v)$", "", t, flags=re.I)
    t = re.sub(r"\s*\(\d+\)\s*$", "", t)            # drop "(1)" copy markers
    t = re.sub(r"\s*\(1080p[^)]*\)", "", t, flags=re.I)
    t = t.replace("_", " ").replace("Sasha s Uplearn", "").strip(" -_")
    t = re.sub(r"\s+", " ", t)
    return t or "Lesson"

# ---- fetch -----------------------------------------------------------------
items = httpx.get(
    f"https://video.bunnycdn.com/library/{LIB}/videos?itemsPerPage=100",
    headers={"AccessKey": KEY}, timeout=30,
).json()["items"]
ready = [v for v in items if v.get("status") == 4]
print(f"ready videos: {len(ready)}")

# ---- classify + dedup ------------------------------------------------------
# Each course: {dedup_key: (order, raw_title, guid, length)} -> keep longest.
courses = {
    "fullstack": {"title": "Fullstack Web Development with AI — Tamil",
                  "cat": "Web Development",
                  "desc": "Beginner-friendly fullstack web development in Tamil: HTML, CSS, JavaScript, React, Node.js, MongoDB and authentication, built with AI tooling.",
                  "L": {}},
    "aitools":   {"title": "AI Tools for Developers — Tamil",
                  "cat": "Artificial Intelligence",
                  "desc": "Hands-on tour of modern AI coding tools: OpenAI, Claude, Gemini, Amazon Q, Codeium/Windsurf and AWS — in Tamil.",
                  "L": {}},
    "excel":     {"title": "Microsoft Excel Mastery",
                  "cat": "Office Productivity",
                  "desc": "Practical Microsoft Excel: formulas, functions, sorting, filtering, conditional formatting, charts and pivot tables.",
                  "L": {}},
}

AI_ORDER = ["overview", "intro", "openai", "claude", "gemini", "amazonq", "codeium", "aws"]
EXCEL_ORDER = ["excelintro", "takealook", "basicformulas", "relativeabsolute", "ifcondition",
               "statistical", "sortfilter", "datavalidation", "conditionalformat", "charts", "pivot"]

def add(course, key, order, raw, g, length):
    cur = courses[course]["L"].get(key)
    if not cur or length > cur[0]:
        courses[course]["L"][key] = (length, order, raw, g)  # store length first for max-compare

for v in ready:
    raw, g, length = v["title"], v["guid"], v.get("length", 0)
    t = raw.lower()
    epm = re.search(r"ep\s*0*(\d+)", t)

    is_excel = ("excel" in t or any(k in t for k in
                ["pivot", "charts_graphs", "data_validation", "if_condition", "sort_and_filter",
                 "conditional_formatting", "relative_absolute", "statistical_function",
                 "basic_formulas", "take_a_look"]))
    is_ai = ("_ai_" in t or any(k in t for k in
             ["open_ai", "claude", "gemini", "amazon_q", "codeium", "aws_conclusion", "ai_intro"])
             or ("overview" in t and "fswai" in t))

    if is_excel:
        if "pivot" in t: key, o = "pivot", 10
        elif "charts" in t: key, o = "charts", 9
        elif "conditional" in t: key, o = "conditionalformat", 8
        elif "data_validation" in t: key, o = "datavalidation", 7
        elif "sort" in t: key, o = "sortfilter", 6
        elif "statistical" in t: key, o = "statistical", 5
        elif "if_condition" in t: key, o = "ifcondition", 4
        elif "relative" in t: key, o = "relativeabsolute", 3
        elif "basic_formulas" in t: key, o = "basicformulas", 2
        elif "take_a_look" in t: key, o = "takealook", 1
        elif "excel_intro" in t or "excel intro" in t: key, o = "excelintro", 0
        else: key, o = re.sub(r"[^a-z]", "", t)[:16], 50
        add("excel", key, o, raw, g, length)
    elif epm:
        ep = int(epm.group(1))
        add("fullstack", f"ep{ep:02d}", ep, raw, g, length)
    elif is_ai:
        if "amazon_q" in t: key = "amazonq"
        elif "open_ai" in t: key = "openai"
        elif "codeium" in t: key = "codeium"
        elif "aws" in t: key = "aws"
        elif "claude" in t: key = "claude"
        elif "gemini" in t: key = "gemini"
        elif "ai_intro" in t: key = "intro"
        elif "overview" in t: key = "overview"
        else: key = re.sub(r"[^a-z]", "", t)[:16]
        o = AI_ORDER.index(key) if key in AI_ORDER else 50
        add("aitools", key, o, raw, g, length)
    elif "intro" in t and "fswai" in t:
        add("fullstack", "ep00", 0, raw, g, length)
    # else: skip junk (videoplayback.m4v etc.)

# ---- DB --------------------------------------------------------------------
conn = psycopg2.connect(DB); conn.autocommit = False
cur = conn.cursor()

# instructor
cur.execute("SELECT id FROM users WHERE user_email=%s", (INSTRUCTOR_EMAIL,))
row = cur.fetchone()
if row:
    instr_id = row[0]
    print(f"instructor exists: id={instr_id}")
else:
    cur.execute(
        """INSERT INTO users (user_login,user_email,user_pass,user_nicename,display_name,
                              role,is_active,is_verified,user_status)
           VALUES (%s,%s,%s,%s,%s,'instructor',true,true,1) RETURNING id""",
        ("sasha_instructor", INSTRUCTOR_EMAIL, get_password_hash(INSTRUCTOR_PASS),
         "sasha-instructor", "Sasha Infinity"))
    instr_id = cur.fetchone()[0]
    cur.execute("INSERT INTO user_profiles (user_id,first_name,last_name) VALUES (%s,'Sasha','Infinity')", (instr_id,))
    cur.execute("INSERT INTO instructor_profiles (user_id,is_approved,is_blocked) VALUES (%s,true,false)", (instr_id,))
    print(f"created instructor: id={instr_id} ({INSTRUCTOR_EMAIL} / {INSTRUCTOR_PASS})")

summary = []
for ckey, c in courses.items():
    lessons = sorted(c["L"].values(), key=lambda x: (x[1], x[2]))  # by order, then title
    if not lessons:
        continue
    cur.execute("SELECT id FROM courses WHERE post_title=%s", (c["title"],))
    ex = cur.fetchone()
    if ex:
        print(f"course already exists, skipping: {c['title']} (id={ex[0]})")
        continue
    total_sec = sum(x[0] for x in lessons)
    slug = re.sub(r"[^a-z0-9]+", "-", c["title"].lower()).strip("-")
    first_guid = lessons[0][3]
    cur.execute(
        """INSERT INTO courses
           (post_author,post_title,post_content,post_excerpt,post_status,post_name,post_type,
            course_price_type,course_price,course_level,course_language,course_category,
            course_duration,course_thumbnail,num_hours)
           VALUES (%s,%s,%s,%s,'publish',%s,'courses','free',0,'beginner','Tamil',%s,%s,%s,%s)
           RETURNING id""",
        (instr_id, c["title"], c["desc"], c["desc"][:140], slug, c["cat"],
         f"{total_sec // 3600}h {total_sec % 3600 // 60}m", poster(first_guid),
         max(1, total_sec // 3600)))
    cid = cur.fetchone()[0]
    for i, (length, order, raw, g) in enumerate(lessons, start=1):
        cur.execute(
            """INSERT INTO lessons
               (post_author,post_title,post_status,post_type,post_parent,menu_order,
                lesson_video_source,lesson_video_url,lesson_video_poster,lesson_video_duration,lesson_preview)
               VALUES (%s,%s,'publish','lesson',%s,%s,'bunny',%s,%s,%s,%s)""",
            (instr_id, clean(raw), cid, i, hls(g), poster(g), dur(length), i == 1))
    summary.append((c["title"], cid, len(lessons)))

conn.commit()
print("\n=== seeded ===")
for title, cid, n in summary:
    print(f"  course {cid}: {title}  ({n} lessons)")
cur.close(); conn.close()
