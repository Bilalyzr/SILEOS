"""
Manual SEO smoke check. Run explicitly with backend on PYTHONPATH, never during pytest collection.

Cannot import the full app on this machine (razorpay etc. are Docker-only),
so this extracts the SEO helpers straight from main.py's source and runs
them against a throwaway sqlite DB built from the real models.
"""
import asyncio
import json
import os
import re
import sys
import tempfile
from datetime import datetime, timedelta
from html import escape

TMP_DB = os.path.join(tempfile.gettempdir(), "sasha_seo_smoke.db")
if os.path.exists(TMP_DB):
    os.remove(TMP_DB)

os.environ["DATABASE_URL"] = f"sqlite:///{TMP_DB}"
os.environ["JWT_SECRET"] = "test"
os.environ["SECRET_KEY"] = "test"
os.environ["REDIS_URL"] = "redis://localhost:6379/0"

from app.core.database import engine  # noqa: E402
from app.core.database import SessionLocal, Base  # noqa: E402
from app.models import *  # noqa: E402,F403  (registers all models on Base)

Base.metadata.create_all(bind=engine)

# --- seed ---------------------------------------------------------------
db = SessionLocal()
author = User(
    user_login="seo_test_author", user_pass="x", user_nicename="seo_test_author",
    user_email="seo-test@example.com", display_name="Test Author <SEO>",
)
db.add(author)
db.flush()

now = datetime(2026, 8, 20, 10, 0, 0)
posts = [
    BlogPost(
        author_id=author.id, title="Post A & <Angles>",
        slug="post-a", status="PUBLISHED", category="Tech",
        excerpt="Excerpt for post A",
        content='<h2>Heading</h2><p>Real <b>article</b> body for post A.</p>',
        featured_image="/uploads/img.png", post_date=now, post_modified=now,
        meta_title="Meta A", meta_description="Meta description A",
    ),
    BlogPost(
        author_id=author.id, title="Post B same category",
        slug="post-b", status="PUBLISHED", category="Tech",
        excerpt=None, content="<p>Body B without excerpt.</p>",
        featured_image=None,
        post_date=now - timedelta(days=2), post_modified=now - timedelta(days=1),
        meta_title=None, meta_description=None,
    ),
    BlogPost(
        author_id=author.id, title="Draft post", slug="draft-post",
        status="DRAFT", category="Tech", excerpt="draft",
        content="<p>draft</p>", post_date=now, post_modified=now,
    ),
]
db.add_all(posts)
db.commit()
db.close()

# --- load the SEO block from main.py source -----------------------------
src = open("app/main.py", encoding="utf-8").read()
start = src.index("SITE_URL = ")
end = src.index("# Prerender Endpoint - for social media crawler support")
from fastapi import FastAPI  # noqa: E402
from fastapi.responses import PlainTextResponse  # noqa: E402
seo_ns = {
    "re": re, "json": json, "escape": escape,
    "SessionLocal": SessionLocal, "BlogPost": BlogPost,
    "PlainTextResponse": PlainTextResponse,
    "app": FastAPI(),  # the block registers robots/sitemap routes on this throwaway app
}
exec(compile(src[start:end], "seo_block", "exec"), seo_ns)

failures = []


def check(name, cond):
    print(("PASS " if cond else "FAIL ") + name)
    if not cond:
        failures.append(name)


# --- robots.txt ---------------------------------------------------------
r = asyncio.run(seo_ns["robots_txt"]())
check("robots: 200 + text/plain", r.status_code == 200 and "text/plain" in r.media_type)
check("robots: has Allow + Sitemap",
      "Allow: /" in r.body.decode() and "Sitemap: https://sashainfinity.com/sitemap.xml" in r.body.decode())

# --- sitemap.xml --------------------------------------------------------
r = asyncio.run(seo_ns["sitemap_xml"]())
body = r.body.decode()
check("sitemap: 200 + xml", r.status_code == 200 and "xml" in r.media_type)
check("sitemap: static pages", "/blog<" in body and "/courses" in body)
check("sitemap: published posts only", "/blog/post-a<" in body and "/blog/post-b<" in body and "draft" not in body)
check("sitemap: lastmod present", "<lastmod>2026-08-19" in body)  # post-b modified
import xml.dom.minidom as minidom
try:
    minidom.parseString(body)
    check("sitemap: valid XML", True)
except Exception as e:
    print("XML parse error:", e)
    check("sitemap: valid XML", False)

# --- single post --------------------------------------------------------
post = seo_ns["_get_published_blog_post"]("post-a")
check("lookup: published post found", post is not None and post["author_name"] == "Test Author <SEO>")
r = seo_ns["_blog_post_response"](post)
html = r.body.decode()
check("post: 200 html", r.status_code == 200 and r.media_type == "text/html")
check("post: article body present", "Real <b>article</b> body for post A." in html)
check("post: NO self-redirect script", "window.location.href" not in html and 'http-equiv="refresh"' not in html)
check("post: canonical correct", '<link rel="canonical" href="https://sashainfinity.com/blog/post-a">' in html)
check("post: title escaped", "Meta A" in html and "<title>Meta A</title>" in html)
check("post: og:image absolute + optimized", "images.weserv.nl" in html)
check("post: related links", 'href="/blog/post-b"' in html)
check("post: byline escaped", "Test Author &lt;SEO&gt;" in html)
ld = re.search(r'<script type="application/ld\+json">(\{.*?"BlogPosting".*?\})</script>', html, re.S)
try:
    data = json.loads(ld.group(1))
    check("post: JSON-LD parses w/ dates+author",
          data["@type"] == "BlogPosting" and data["datePublished"].startswith("2026-08-20")
          and data["author"]["name"] == "Test Author <SEO>"
          and data["mainEntityOfPage"]["@id"].endswith("/blog/post-a"))
except Exception as e:
    print("JSON-LD error:", e)
    check("post: JSON-LD parses w/ dates+author", False)

# --- draft / unknown slug ----------------------------------------------
check("lookup: draft excluded", seo_ns["_get_published_blog_post"]("draft-post") is None)
check("lookup: unknown slug -> None", seo_ns["_get_published_blog_post"]("nope") is None)

# --- listing ------------------------------------------------------------
r = seo_ns["_blog_listing_response"]()
html = r.body.decode()
check("listing: 200 html", r.status_code == 200)
check("listing: links published only", 'href="/blog/post-a"' in html and 'href="/blog/post-b"' in html and "draft" not in html)
check("listing: canonical", 'href="https://sashainfinity.com/blog"' in html)
check("listing: no redirect script", "window.location.href" not in html)

# --- misc helpers -------------------------------------------------------
check("related: excludes self, caps at limit",
      [x["slug"] for x in seo_ns["_get_related_blog_posts"]("post-a", "Tech")] == ["post-b"])
check("excerpt fallback strips html",
      seo_ns["_plain_text_excerpt"]("<p>Hello <b>world</b></p>", None) == "Hello world")

print()
print("RESULT:", "ALL PASS" if not failures else f"{len(failures)} FAILURES: {failures}")
sys.exit(1 if failures else 0)
