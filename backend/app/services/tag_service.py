"""Emergent taxonomy (v2.0 §3 — WP4): free tags for instructors, clusters
nobody authored for search.

Tags stay exactly what instructors typed (`courses.course_tags`, a JSON list
of strings). Behind the scenes we cluster them by:
  1. normalisation (case, punctuation, separators, naive plural)
  2. string similarity (character trigram Jaccard)
  3. prefix relation on single tokens ("trig" → "trigonometry")
  4. co-occurrence on the same course (weak similarity + ≥2 shared courses)
with union-find, and store the result in `tag_clusters` (rebuilt lazily when
older than CLUSTER_TTL, or on demand by an admin). Search expands a query to
every member of any cluster it touches. Admins may give a cluster a display
label; the system works without that ever happening.

No embeddings are required; when a GLM key is configured a later pass can
add centroid embeddings — the table already has the column.
"""
from __future__ import annotations

import json
import re
from collections import Counter, defaultdict
from datetime import datetime, timedelta, timezone
from typing import Dict, Iterable, List, Optional, Set, Tuple

from sqlalchemy.orm import Session

from app.models.tag_cluster import TagCluster

CLUSTER_TTL = timedelta(minutes=10)
TRIGRAM_THRESHOLD = 0.55
COOCCUR_MIN_COURSES = 2
COOCCUR_SIM_THRESHOLD = 0.3
PREFIX_MIN = 4
MAX_SUGGESTIONS = 8

STOPWORDS = set("""a an the and or of for to in on with by from at is are be this that these those your you we our
course courses learn learning lesson lessons class classes introduction intro basics basic complete guide
full how what why when into using use used about over under between more most new best free paid online
video videos students student teacher teachers skill skills level beginner intermediate advanced part
while appears appear appeared creating create created creates option options verifying verify verified
also will can could should would make makes made making get gets got take takes taking need needs
help helps helped every each some many much very just only than then there their them they have has
had been being which where who whom its after before during without within through across along
here your yours mine ours own same other another such both either neither because since until
does doing done goes going went come comes coming know knows learnt taught teach teaches show shows
showing find finds finding start starts starting end ends ending simple easy hard quick long short
first last next previous week weeks day days month months year years hour hours minute minutes""".split())


def normalize_tag(raw: str) -> str:
    s = str(raw or "").strip().lower()
    s = re.sub(r"[_\-/]+", " ", s)
    s = re.sub(r"[^a-z0-9஀-௿ ]+", "", s)   # keep Tamil block
    s = " ".join(s.split())
    tokens = []
    for t in s.split(" "):
        if len(t) > 3 and t.endswith("s") and not t.endswith("ss"):
            t = t[:-1]
        tokens.append(t)
    return " ".join(t for t in tokens if t)


def trigrams(s: str) -> Set[str]:
    s = f"  {s} "
    return {s[i:i + 3] for i in range(len(s) - 2)} if len(s) >= 3 else {s}


def similarity(a: str, b: str) -> float:
    na, nb = normalize_tag(a), normalize_tag(b)
    if not na or not nb:
        return 0.0
    if na == nb:
        return 1.0
    ta, tb = trigrams(na), trigrams(nb)
    tri = len(ta & tb) / len(ta | tb) if (ta | tb) else 0.0
    wa, wb = set(na.split()), set(nb.split())
    tok = len(wa & wb) / len(wa | wb) if (wa | wb) else 0.0
    return max(tri, tok)


GENERIC_TOKENS = set("""class classe grade level chapter unit basic basics intro introduction math maths
science part module standard std board exam prep practice test tests""".split())


def _distinctive_tokens(tag: str) -> List[str]:
    return [t for t in normalize_tag(tag).split() if len(t) >= PREFIX_MIN and t not in GENERIC_TOKENS and not t.isdigit()]


def _token_link(a: str, b: str) -> bool:
    """'trig' ↔ 'trigonometry', 'maths-trig' ↔ 'trig', 'class10-trigo' ↔ 'trigonometry':
    two tags link when a distinctive token of one equals, or is a ≥4-char prefix
    of, a distinctive token of the other. Generic tokens (class, maths, …) and
    numbers never link on their own."""
    for ta in _distinctive_tokens(a):
        for tb in _distinctive_tokens(b):
            if ta == tb:
                return True
            short, long_ = (ta, tb) if len(ta) <= len(tb) else (tb, ta)
            if long_.startswith(short):
                return True
    return False


def _is_prefix_pair(a: str, b: str) -> bool:
    return _token_link(a, b)


def load_course_tags(db: Session) -> List[Tuple[int, List[str]]]:
    from app.models.course import Course
    out = []
    for cid, raw in db.query(Course.id, Course.course_tags).filter(Course.post_status == "publish").all():
        try:
            tags = json.loads(raw) if raw else []
        except Exception:
            tags = []
        if isinstance(tags, list):
            out.append((cid, [str(t).strip() for t in tags if str(t).strip()]))
    return out


def compute_clusters(course_tags: List[Tuple[int, List[str]]]) -> List[List[str]]:
    """Union-find over raw tags. Returns clusters (lists of raw tags) of size ≥ 1."""
    raw_tags: List[str] = sorted({t for _, tags in course_tags for t in tags}, key=str.lower)
    if not raw_tags:
        return []
    parent = {t: t for t in raw_tags}

    def find(x):
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    def union(a, b):
        ra, rb = find(a), find(b)
        if ra != rb:
            parent[rb] = ra

    cooc: Dict[Tuple[str, str], int] = Counter()
    for _, tags in course_tags:
        uniq = sorted(set(tags), key=str.lower)
        for i in range(len(uniq)):
            for j in range(i + 1, len(uniq)):
                cooc[(uniq[i], uniq[j])] += 1
    for i in range(len(raw_tags)):
        for j in range(i + 1, len(raw_tags)):
            a, b = raw_tags[i], raw_tags[j]
            sim = similarity(a, b)
            if sim >= TRIGRAM_THRESHOLD or _is_prefix_pair(a, b):
                union(a, b)
            elif cooc.get((a, b), 0) >= COOCCUR_MIN_COURSES and sim >= COOCCUR_SIM_THRESHOLD:
                union(a, b)
    groups: Dict[str, List[str]] = defaultdict(list)
    for t in raw_tags:
        groups[find(t)].append(t)
    return sorted(groups.values(), key=lambda g: (-len(g), g[0].lower()))


def recluster(db: Session) -> List[TagCluster]:
    """Rebuild tag_clusters, carrying labels over by member overlap."""
    old = db.query(TagCluster).all()
    old_labels = [(set(c.member_tags or []), c.label) for c in old if c.label]
    clusters = compute_clusters(load_course_tags(db))
    for c in old:
        db.delete(c)
    db.flush()
    rows = []
    now = datetime.now(timezone.utc)
    for members in clusters:
        label = None
        best = 0
        for old_members, old_label in old_labels:
            overlap = len(old_members & set(members))
            if overlap > best:
                best, label = overlap, old_label
        row = TagCluster(label=label, member_tags=members, size=len(members), updated_at=now)
        db.add(row)
        rows.append(row)
    db.commit()
    return rows


def clusters_fresh(db: Session) -> List[TagCluster]:
    rows = db.query(TagCluster).all()
    stale = not rows or any((r.updated_at is None) or
                            ((datetime.now(timezone.utc) - (r.updated_at if r.updated_at.tzinfo else r.updated_at.replace(tzinfo=timezone.utc))) > CLUSTER_TTL)
                            for r in rows[:1])
    if stale:
        try:
            rows = recluster(db)
        except Exception:
            db.rollback()
            rows = db.query(TagCluster).all()
    return rows


def expand_query(db: Session, q: str) -> List[str]:
    """Tags a search term should match: direct hits plus their cluster members."""
    nq = normalize_tag(q)
    if not nq:
        return []
    hits: Set[str] = set()
    rows = clusters_fresh(db)
    for c in rows:
        members = c.member_tags or []
        touched = any(nq in normalize_tag(m) or normalize_tag(m) in nq or similarity(nq, m) >= TRIGRAM_THRESHOLD
                      or _token_link(nq, m) for m in members) or (c.label and nq in normalize_tag(c.label))
        if touched:
            hits.update(members)
    return sorted(hits, key=str.lower)


def aliases_for(db: Session, tag: str) -> List[str]:
    nt = normalize_tag(tag)
    for c in clusters_fresh(db):
        members = c.member_tags or []
        if any(normalize_tag(m) == nt for m in members):
            return [m for m in members if normalize_tag(m) != nt]
    return []


def suggest_tags(db: Session, title: str, description: str = "", existing: Iterable[str] = ()) -> List[str]:
    """Suggestions derived from the course content itself: known tags that
    appear in the text first, then salient words from the title/description."""
    text = f"{title or ''} {description or ''}".lower()
    text = re.sub(r"<[^>]+>", " ", text)
    have = {normalize_tag(t) for t in existing}
    out: List[str] = []
    known = Counter()
    for _, tags in load_course_tags(db):
        for t in tags:
            known[t] += 1
    for t, _ in known.most_common():
        nt = normalize_tag(t)
        if nt and nt not in have and re.search(r"\b" + re.escape(nt.split()[0]) + r"", text):
            out.append(t)
            have.add(nt)
        if len(out) >= MAX_SUGGESTIONS:
            return out
    words = re.findall(r"[a-z][a-z0-9+#]{3,}", text)
    freq = Counter(w for w in words if w not in STOPWORDS)
    title_words = set(re.findall(r"[a-z][a-z0-9+#]{3,}", (title or "").lower()))
    ranked = sorted(freq.items(), key=lambda kv: (-(kv[1] + (2 if kv[0] in title_words else 0)), kv[0]))
    for w, _ in ranked:
        nw = normalize_tag(w)
        if nw and nw not in have:
            out.append(w)
            have.add(nw)
        if len(out) >= MAX_SUGGESTIONS:
            break
    return out
