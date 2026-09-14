"""
Tags Router - SashaInfinity LMS API
Handles course tag endpoints
"""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from typing import List, Dict, Any

from app.core.database import get_db
from app.models.course import CourseTag

router = APIRouter()


@router.get("/", response_model=List[Dict[str, Any]])
def get_tags(db: Session = Depends(get_db)):
    """Get all course tags"""
    tags = db.query(CourseTag).order_by(CourseTag.name).all()
    result = []
    for tag in tags:
        result.append({
            "id": tag.id,
            "name": tag.name,
            "slug": tag.slug,
            "description": tag.description,
        })
    return result
