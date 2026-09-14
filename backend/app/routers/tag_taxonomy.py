"""Emergent taxonomy API (v2.0 §3 — WP4) at /api/v1/tag-taxonomy (no trailing slashes;
the legacy GET /api/v1/tags/ listing stays in routers/tags.py).

  GET  /suggest?title=&description=&existing=a,b   instructor: suggested tags on save
  GET  /expand?q=                                 what a search term expands to
  GET  /aliases?tag=                              cluster-mates of one tag
  GET  /clusters                                  public: clusters (+ optional labels)
  POST /clusters/recluster                        admin: rebuild now
  PUT  /clusters/{id}                             admin: set/clear the display label
"""
from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.tag_cluster import TagCluster
from app.models.user import User
from app.services import tag_service as ts
from app.services.auth_service import AuthService

router = APIRouter()


def _cluster_dict(c: TagCluster) -> dict:
    return {"id": c.id, "label": c.label, "member_tags": c.member_tags or [], "size": c.size, "updated_at": c.updated_at}


@router.get("/suggest")
async def suggest(title: str = Query("", max_length=300), description: str = Query("", max_length=5000),
                  existing: str = Query("", max_length=1000), db: Session = Depends(get_db),
                  current_user: User = Depends(AuthService.require_instructor)):
    have = [t.strip() for t in existing.split(",") if t.strip()]
    return {"suggestions": ts.suggest_tags(db, title, description, have)}


@router.get("/expand")
async def expand(q: str = Query(..., min_length=1, max_length=120), db: Session = Depends(get_db)):
    return {"q": q, "tags": ts.expand_query(db, q)}


@router.get("/aliases")
async def aliases(tag: str = Query(..., min_length=1, max_length=200), db: Session = Depends(get_db)):
    return {"tag": tag, "aliases": ts.aliases_for(db, tag)}


@router.get("/clusters")
async def clusters(db: Session = Depends(get_db)):
    rows = ts.clusters_fresh(db)
    return {"clusters": [_cluster_dict(c) for c in sorted(rows, key=lambda c: (-(c.size or 0), c.id))]}


@router.post("/clusters/recluster")
async def recluster_now(db: Session = Depends(get_db), current_user: User = Depends(AuthService.require_admin)):
    rows = ts.recluster(db)
    return {"clusters": len(rows), "tags": sum(c.size or 0 for c in rows)}


class LabelIn(BaseModel):
    label: Optional[str] = Field(None, max_length=120)


@router.put("/clusters/{cluster_id}")
async def set_label(cluster_id: int, payload: LabelIn, db: Session = Depends(get_db),
                    current_user: User = Depends(AuthService.require_admin)):
    c = db.query(TagCluster).filter(TagCluster.id == cluster_id).first()
    if not c:
        raise HTTPException(status_code=404, detail="Cluster not found")
    c.label = (payload.label or "").strip() or None
    db.commit()
    db.refresh(c)
    return _cluster_dict(c)
