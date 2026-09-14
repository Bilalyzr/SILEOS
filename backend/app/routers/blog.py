import re
"""
Blog API Routes
"""
from fastapi import APIRouter, Depends, HTTPException, status, Query, UploadFile, Response
from sqlalchemy.orm import Session, joinedload
from typing import List, Optional
from datetime import datetime
from slugify import slugify
import logging

# Get logger for this module
logger = logging.getLogger(__name__)

from app.core.database import get_db
from app.models.blog import BlogPost, BlogComment
from app.models.user import User
from app.models.course import Course
from app.models.internship import Internship
from app.services.auth_service import AuthService
from pydantic import BaseModel
import json


router = APIRouter(tags=["Blog"])


# Pydantic schemas
class BlogPostCreate(BaseModel):
    title: str
    content: str
    excerpt: Optional[str] = None
    featured_image: Optional[str] = None
    category: Optional[str] = None
    tags: Optional[str] = None
    meta_title: Optional[str] = None
    meta_description: Optional[str] = None
    status: str = "DRAFT"  # DRAFT or PUBLISHED
    related_course_ids: Optional[List[int]] = []
    related_internship_ids: Optional[List[int]] = []


class BlogPostUpdate(BaseModel):
    title: Optional[str] = None
    content: Optional[str] = None
    excerpt: Optional[str] = None
    featured_image: Optional[str] = None
    category: Optional[str] = None
    tags: Optional[str] = None
    meta_title: Optional[str] = None
    meta_description: Optional[str] = None
    status: Optional[str] = None
    related_course_ids: Optional[List[int]] = None
    related_internship_ids: Optional[List[int]] = None


class BlogPostResponse(BaseModel):
    id: int
    title: str
    slug: str
    content: str
    excerpt: Optional[str]
    featured_image: Optional[str]
    status: str
    category: Optional[str]
    tags: Optional[str]
    view_count: int
    comment_count: int
    post_date: datetime
    post_modified: datetime
    author: dict
    related_course_ids: List[int] = []
    related_internship_ids: List[int] = []
    related_courses: List[dict] = []
    related_internships: List[dict] = []

    class Config:
        from_attributes = True


class BlogPostEditResponse(BlogPostResponse):
    """Editor payload — same shape as the reader plus the SEO meta fields the
    edit form binds to (BlogPostResponse omits them, and response_model would
    strip them out)."""
    meta_title: Optional[str] = None
    meta_description: Optional[str] = None


class BlogCommentCreate(BaseModel):
    content: str


class BlogCommentResponse(BaseModel):
    id: int
    content: str
    status: str
    created_at: datetime
    user: dict

    class Config:
        from_attributes = True


# Helper function to generate unique slug
def generate_unique_slug(title: str, db: Session, post_id: Optional[int] = None) -> str:
    base_slug = slugify(title)
    slug = base_slug
    counter = 1

    while True:
        query = db.query(BlogPost).filter(BlogPost.slug == slug)
        if post_id:
            query = query.filter(BlogPost.id != post_id)

        if not query.first():
            return slug

        slug = f"{base_slug}-{counter}"
        counter += 1



def clean_content(content: str) -> str:
    if not content:
        return ""
    import re
    # Replace literal \n and \t escape sequences
    content = content.replace("\\n", "<br>")
    content = content.replace("\\t", "&nbsp;&nbsp;")
    content = content.replace("\n", "<br>")
    content = content.replace("\t", "&nbsp;&nbsp;")
    return content


def get_related_items(post: BlogPost, db: Session) -> tuple:
    """Get related courses and internships for a blog post."""
    related_courses = []
    related_internships = []

    # Parse related course IDs
    course_ids = []
    if post.related_course_ids:
        try:
            course_ids = json.loads(post.related_course_ids) if isinstance(post.related_course_ids, str) else post.related_course_ids
        except:
            course_ids = []

    if course_ids:
        courses = db.query(Course).filter(Course.id.in_(course_ids)).all()
        related_courses = [
            {"id": c.id, "title": c.post_title, "slug": c.post_name or f"course-{c.id}", "thumbnail": c.course_thumbnail}
            for c in courses
        ]

    # Parse related internship IDs
    internship_ids = []
    if post.related_internship_ids:
        try:
            internship_ids = json.loads(post.related_internship_ids) if isinstance(post.related_internship_ids, str) else post.related_internship_ids
        except:
            internship_ids = []

    if internship_ids:
        internships = db.query(Internship).filter(Internship.id.in_(internship_ids)).all()
        related_internships = [
            {"id": i.id, "title": i.title, "slug": i.slug, "cover_image": i.cover_image}
            for i in internships
        ]

    return related_courses, related_internships

@router.get("/", response_model=List[BlogPostResponse])
async def get_blog_posts(
    response: Response,
    skip: int = Query(0, ge=0),
    limit: int = Query(10, ge=1, le=100),
    category: Optional[str] = None,
    search: Optional[str] = None,
    status: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """Get all blog posts (public and published only by default)"""
    query = db.query(BlogPost).options(joinedload(BlogPost.author))

    # Filter by status (default to PUBLISHED for public access)
    if status:
        query = query.filter(BlogPost.status == status.upper())
    else:
        query = query.filter(BlogPost.status == "PUBLISHED")

    # Filter by category
    if category:
        query = query.filter(BlogPost.category == category)

    # Search by title or content
    if search:
        query = query.filter(
            (BlogPost.title.ilike(f"%{search}%")) |
            (BlogPost.content.ilike(f"%{search}%"))
        )

    # Order by post_date descending
    query = query.order_by(BlogPost.post_date.desc())

    # Total after filters, before pagination — lets clients build page controls
    # without changing this endpoint's list-shaped response body.
    total = query.count()
    response.headers["X-Total-Count"] = str(total)

    # Pagination
    posts = query.offset(skip).limit(limit).all()

    # Format response
    result = []
    for post in posts:
        related_courses, related_internships = get_related_items(post, db)
        result.append({
            "id": post.id,
            "title": post.title,
            "slug": post.slug,
            "content": clean_content(post.content),
            "excerpt": re.sub(r'<[^>]+>', '', post.excerpt or '').replace('\\n',' ').replace('\\t',' ').strip()[:300] if post.excerpt else "",
            "featured_image": post.featured_image,
            "status": post.status,
            "category": post.category,
            "tags": post.tags,
            "view_count": post.view_count or 0,
            "comment_count": post.comment_count or 0,
            "post_date": post.post_date,
            "post_modified": post.post_modified,
            "author": {
                "id": post.author.id if post.author else 4,
                "name": post.author.display_name if post.author else "SashaInfinity",
                "email": post.author.user_email if post.author else "admin@sashainfinity.com"
            },
            "related_course_ids": json.loads(post.related_course_ids) if post.related_course_ids else [],
            "related_internship_ids": json.loads(post.related_internship_ids) if post.related_internship_ids else [],
            "related_courses": related_courses,
            "related_internships": related_internships
        })
    return result


@router.get("/id/{post_id}", response_model=BlogPostEditResponse)
async def get_blog_post_for_edit(
    post_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(AuthService.get_current_active_user)
):
    """
    Get a single blog post by id for editing (author or admin only).

    Deliberately separate from the public `GET /blog/{slug}` reader:
      * looks up by id — the editor only has the id from the admin/instructor list
      * returns raw `content` and the full `excerpt`; the reader runs both
        through clean_content()/tag-stripping + a 300-char cut, which would be
        written straight back to the database on the next save
      * returns meta_title/meta_description, which the editor form has fields for
      * does NOT increment view_count — opening the editor is not a page view
    """
    post = db.query(BlogPost).options(
        joinedload(BlogPost.author)
    ).filter(BlogPost.id == post_id).first()

    if not post:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Blog post not found"
        )

    # Same rule as update_blog_post/delete_blog_post: author or admin.
    if post.author_id != current_user.id and current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only edit your own blog posts"
        )

    related_courses, related_internships = get_related_items(post, db)

    return {
        "id": post.id,
        "title": post.title,
        "slug": post.slug,
        "content": post.content or "",
        "excerpt": post.excerpt or "",
        "featured_image": post.featured_image,
        "status": post.status,
        "category": post.category,
        "tags": post.tags,
        "meta_title": post.meta_title,
        "meta_description": post.meta_description,
        "view_count": post.view_count or 0,
        "comment_count": post.comment_count or 0,
        "post_date": post.post_date,
        "post_modified": post.post_modified,
        "author": {
            "id": post.author.id if post.author else post.author_id,
            "name": post.author.display_name if post.author else "Unknown",
            "email": post.author.user_email if post.author else ""
        },
        "related_course_ids": json.loads(post.related_course_ids) if post.related_course_ids else [],
        "related_internship_ids": json.loads(post.related_internship_ids) if post.related_internship_ids else [],
        "related_courses": related_courses,
        "related_internships": related_internships
    }


@router.get("/{slug}", response_model=BlogPostResponse)
async def get_blog_post(
    slug: str,
    db: Session = Depends(get_db)
):
    """Get a single blog post by slug"""
    post = db.query(BlogPost).options(
        joinedload(BlogPost.author)
    ).filter(BlogPost.slug == slug).first()

    if not post:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Blog post not found"
        )

    # Increment view count
    post.view_count = (post.view_count or 0) + 1
    db.commit()

    related_courses, related_internships = get_related_items(post, db)

    return {
        "id": post.id,
        "title": post.title,
        "slug": post.slug,
        "content": clean_content(post.content),
        "excerpt": re.sub(r'<[^>]+>', '', post.excerpt or '').replace('\\n',' ').replace('\\t',' ').strip()[:300] if post.excerpt else "",
        "featured_image": post.featured_image,
        "status": post.status,
        "category": post.category,
        "tags": post.tags,
        "view_count": post.view_count or 0,
        "comment_count": post.comment_count or 0,
        "post_date": post.post_date,
        "post_modified": post.post_modified,
        "author": {
            "id": post.author.id if post.author else 4,
            "name": post.author.display_name if post.author else "SashaInfinity",
            "email": post.author.user_email if post.author else "admin@sashainfinity.com"
        },
        "related_course_ids": json.loads(post.related_course_ids) if post.related_course_ids else [],
        "related_internship_ids": json.loads(post.related_internship_ids) if post.related_internship_ids else [],
        "related_courses": related_courses,
        "related_internships": related_internships
    }

# Handle GET requests without trailing slash by delegating to the main function
@router.get("", response_model=List[BlogPostResponse])
async def get_blog_posts_no_slash(
    response: Response,
    skip: int = Query(0, ge=0),
    limit: int = Query(10, ge=1, le=100),
    category: Optional[str] = None,
    search: Optional[str] = None,
    status: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """Get all blog posts (public and published only by default) - handles requests without trailing slash"""
    return await get_blog_posts(skip=skip, limit=limit, category=category, search=search, status=status, db=db, response=response)

@router.post("/", response_model=BlogPostResponse)
async def create_blog_post(
    post_data: BlogPostCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(AuthService.get_current_active_user)
):
    """Create a new blog post (instructor, spoc, admin, or student)"""
    # Check if user has permission to create blogs
    if current_user.role not in ["instructor", "spoc", "admin", "student"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have permission to create blog posts"
        )

    # Generate unique slug
    slug = generate_unique_slug(post_data.title, db)

    # Students' posts go to PENDING status, others use the requested status
    post_status = post_data.status.upper()
    if current_user.role == "student":
        post_status = "PENDING"

    # Create blog post
    new_post = BlogPost(
        author_id=current_user.id,
        title=post_data.title,
        slug=slug,
        content=post_data.content,
        excerpt=post_data.excerpt,
        featured_image=post_data.featured_image,
        category=post_data.category,
        tags=post_data.tags,
        meta_title=post_data.meta_title or post_data.title,
        meta_description=post_data.meta_description or post_data.excerpt,
        status=post_status,
        related_course_ids=json.dumps(post_data.related_course_ids or []) if post_data.related_course_ids else None,
        related_internship_ids=json.dumps(post_data.related_internship_ids or []) if post_data.related_internship_ids else None
    )

    db.add(new_post)
    db.commit()
    db.refresh(new_post)

    related_courses, related_internships = get_related_items(new_post, db)

    return {
        "id": new_post.id,
        "title": new_post.title,
        "slug": new_post.slug,
        "content": new_post.content,
        "excerpt": new_post.excerpt,
        "featured_image": new_post.featured_image,
        "status": new_post.status,
        "category": new_post.category,
        "tags": new_post.tags,
        "view_count": new_post.view_count,
        "comment_count": new_post.comment_count,
        "post_date": new_post.post_date,
        "post_modified": new_post.post_modified,
        "author": {
            "id": current_user.id,
            "name": current_user.display_name,
            "email": current_user.user_email
        },
        "related_course_ids": json.loads(new_post.related_course_ids) if new_post.related_course_ids else [],
        "related_internship_ids": json.loads(new_post.related_internship_ids) if new_post.related_internship_ids else [],
        "related_courses": related_courses,
        "related_internships": related_internships
    }


@router.put("/{post_id}", response_model=BlogPostResponse)
async def update_blog_post(
    post_id: int,
    post_data: BlogPostUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(AuthService.get_current_active_user)
):
    """Update a blog post (author or admin only)"""
    post = db.query(BlogPost).filter(BlogPost.id == post_id).first()

    if not post:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Blog post not found"
        )

    # Check if user is author or admin
    if post.author_id != current_user.id and current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only edit your own blog posts"
        )

    # Update fields
    update_data = post_data.dict(exclude_unset=True)

    # If title is being updated, regenerate slug
    if "title" in update_data and update_data["title"] != post.title:
        update_data["slug"] = generate_unique_slug(update_data["title"], db, post_id)

    for field, value in update_data.items():
        if field == "status" and value:
            value = value.upper()
        elif field == "related_course_ids" and value is not None:
            value = json.dumps(value) if value else None
        elif field == "related_internship_ids" and value is not None:
            value = json.dumps(value) if value else None
        setattr(post, field, value)

    post.post_modified = datetime.utcnow()
    db.commit()
    db.refresh(post)

    # Load author
    author = db.query(User).filter(User.id == post.author_id).first()
    related_courses, related_internships = get_related_items(post, db)

    return {
        "id": post.id,
        "title": post.title,
        "slug": post.slug,
        "content": post.content.replace("\n", "<br>") if post.content and "<" not in post.content[:100] else post.content,
        "excerpt": re.sub(r'<[^>]+>', '', post.excerpt or '').replace('\\n',' ').replace('\\t',' ').strip()[:300] if post.excerpt else "",
        "featured_image": post.featured_image,
        "status": post.status,
        "category": post.category,
        "tags": post.tags,
        "view_count": post.view_count or 0,
        "comment_count": post.comment_count or 0,
        "post_date": post.post_date,
        "post_modified": post.post_modified,
        "author": {
            "id": author.id,
            "name": author.display_name,
            "email": author.user_email
        },
        "related_course_ids": json.loads(post.related_course_ids) if post.related_course_ids else [],
        "related_internship_ids": json.loads(post.related_internship_ids) if post.related_internship_ids else [],
        "related_courses": related_courses,
        "related_internships": related_internships
    }


@router.delete("/{post_id}")
async def delete_blog_post(
    post_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(AuthService.get_current_active_user)
):
    """Delete a blog post (author or admin only)"""
    post = db.query(BlogPost).filter(BlogPost.id == post_id).first()

    if not post:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Blog post not found"
        )

    # Check if user is author or admin
    if post.author_id != current_user.id and current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only delete your own blog posts"
        )

    db.delete(post)
    db.commit()

    return {"message": "Blog post deleted successfully"}


# Blog Comments
@router.get("/{post_id}/comments", response_model=List[BlogCommentResponse])
async def get_blog_comments(
    post_id: int,
    db: Session = Depends(get_db)
):
    """Get all comments for a blog post"""
    comments = db.query(BlogComment).filter(
        BlogComment.blog_post_id == post_id,
        BlogComment.status == "APPROVED"
    ).options(joinedload(BlogComment.user)).order_by(BlogComment.created_at.desc()).all()

    return [
        {
            "id": comment.id,
            "content": comment.content,
            "status": comment.status,
            "created_at": comment.created_at,
            "user": {
                "id": comment.user.id,
                "name": comment.user.display_name
            }
        }
        for comment in comments
    ]


@router.post("/{post_id}/comments", response_model=BlogCommentResponse)
async def create_blog_comment(
    post_id: int,
    comment_data: BlogCommentCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(AuthService.get_current_user)
):
    """Create a new comment on a blog post"""
    # Check if blog post exists
    post = db.query(BlogPost).filter(BlogPost.id == post_id).first()
    if not post:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Blog post not found"
        )

    # Create comment
    new_comment = BlogComment(
        blog_post_id=post_id,
        user_id=current_user.id,
        content=comment_data.content,
        status="APPROVED"  # Auto-approve for now
    )

    db.add(new_comment)

    # Update comment count
    post.comment_count += 1

    db.commit()
    db.refresh(new_comment)

    return {
        "id": new_comment.id,
        "content": new_comment.content,
        "status": new_comment.status,
        "created_at": new_comment.created_at,
        "user": {
            "id": current_user.id,
            "name": current_user.display_name
        }
    }


@router.get("/instructor/my-posts", response_model=List[BlogPostResponse])
async def get_instructor_blog_posts(
    db: Session = Depends(get_db),
    current_user: User = Depends(AuthService.require_instructor)
):
    """Get all blog posts by current instructor"""
    posts = db.query(BlogPost).filter(
        BlogPost.author_id == current_user.id
    ).order_by(BlogPost.post_date.desc()).all()

    result = []
    for post in posts:
        related_courses, related_internships = get_related_items(post, db)
        result.append({
            "id": post.id,
            "title": post.title,
            "slug": post.slug,
            "content": post.content.replace("\n", "<br>") if post.content and "<" not in post.content[:100] else post.content,
            "excerpt": re.sub(r'<[^>]+>', '', post.excerpt or '').replace('\\n',' ').replace('\\t',' ').strip()[:300] if post.excerpt else "",
            "featured_image": post.featured_image,
            "status": post.status,
            "category": post.category,
            "tags": post.tags,
            "view_count": post.view_count or 0,
            "comment_count": post.comment_count or 0,
            "post_date": post.post_date,
            "post_modified": post.post_modified,
            "author": {
                "id": current_user.id,
                "name": current_user.display_name,
                "email": current_user.user_email
            },
            "related_course_ids": json.loads(post.related_course_ids) if post.related_course_ids else [],
            "related_internship_ids": json.loads(post.related_internship_ids) if post.related_internship_ids else [],
            "related_courses": related_courses,
            "related_internships": related_internships
        })
    return result


@router.get("/spoc/my-posts", response_model=List[BlogPostResponse])
async def get_spoc_blog_posts(
    db: Session = Depends(get_db),
    current_user: User = Depends(AuthService.require_spoc_or_admin)
):
    """Get all blog posts by current SPOC"""
    posts = db.query(BlogPost).filter(
        BlogPost.author_id == current_user.id
    ).order_by(BlogPost.post_date.desc()).all()

    result = []
    for post in posts:
        related_courses, related_internships = get_related_items(post, db)
        result.append({
            "id": post.id,
            "title": post.title,
            "slug": post.slug,
            "content": post.content.replace("\n", "<br>") if post.content and "<" not in post.content[:100] else post.content,
            "excerpt": re.sub(r'<[^>]+>', '', post.excerpt or '').replace('\\n',' ').replace('\\t',' ').strip()[:300] if post.excerpt else "",
            "featured_image": post.featured_image,
            "status": post.status,
            "category": post.category,
            "tags": post.tags,
            "view_count": post.view_count or 0,
            "comment_count": post.comment_count or 0,
            "post_date": post.post_date,
            "post_modified": post.post_modified,
            "author": {
                "id": current_user.id,
                "name": current_user.display_name,
                "email": current_user.user_email
            },
            "related_course_ids": json.loads(post.related_course_ids) if post.related_course_ids else [],
            "related_internship_ids": json.loads(post.related_internship_ids) if post.related_internship_ids else [],
            "related_courses": related_courses,
            "related_internships": related_internships
        })
    return result

# ===== Newsletter Subscription =====
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import os

class NewsletterSubscribe(BaseModel):
    email: str

class ContactForm(BaseModel):
    name: str
    email: str
    message: str

def send_email(to: str, subject: str, body: str):
    try:
        msg = MIMEMultipart()
        msg['From'] = os.getenv('EMAIL_FROM', 'noreply@sashainfinity.com')
        msg['To'] = to
        msg['Subject'] = subject
        msg.attach(MIMEText(body, 'html'))
        with smtplib.SMTP(os.getenv('SMTP_HOST','mail.sashainfinity.com'), int(os.getenv('SMTP_PORT',587))) as server:
            server.starttls()
            server.login(os.getenv('SMTP_USER',''), os.getenv('SMTP_PASSWORD',''))
            server.send_message(msg)
        return True
    except Exception as e:
        logger.error(f"Email error: {e}")
        return False

@router.post("/newsletter/subscribe")
async def newsletter_subscribe(data: NewsletterSubscribe):
    """Subscribe to newsletter"""
    import re
    if not re.match(r'^[^@]+@[^@]+\.[^@]+$', data.email):
        raise HTTPException(status_code=400, detail="Invalid email address")
    # Send confirmation email
    send_email(
        data.email,
        "Welcome to SashaInfinity Newsletter!",
        f"""<h2>Thank you for subscribing!</h2>
        <p>You'll receive the latest updates on courses, AR/VR learning, and mathematics education from SashaInfinity.</p>
        <p>Visit us at <a href="https://lms.sashainfinity.com">lms.sashainfinity.com</a></p>"""
    )
    # Notify admin
    send_email(
        "noreply@sashainfinity.com",
        f"New Newsletter Subscriber: {data.email}",
        f"<p>New subscriber: <strong>{data.email}</strong></p>"
    )
    return {"success": True, "message": "Subscribed successfully!"}

@router.post("/contact/submit")
async def contact_submit(data: ContactForm):
    """Submit contact form"""
    import re
    if not data.name.strip():
        raise HTTPException(status_code=400, detail="Name is required")
    if not re.match(r'^[^@]+@[^@]+\.[^@]+$', data.email):
        raise HTTPException(status_code=400, detail="Invalid email address")
    if len(data.message.strip()) < 10:
        raise HTTPException(status_code=400, detail="Message too short")
    send_email(
        "noreply@sashainfinity.com",
        f"Contact Form: {data.name}",
        f"""<h3>New Contact Form Submission</h3>
        <p><strong>Name:</strong> {data.name}</p>
        <p><strong>Email:</strong> {data.email}</p>
        <p><strong>Message:</strong><br>{data.message}</p>"""
    )
    send_email(
        data.email,
        "We received your message - SashaInfinity",
        f"""<h2>Hi {data.name},</h2>
        <p>Thank you for contacting us! We'll get back to you within 24 hours.</p>
        <p>Team SashaInfinity</p>"""
    )
    return {"success": True, "message": "Message sent successfully!"}


# Blog Image Upload Endpoint
@router.post("/upload-image")
async def upload_blog_image(
    file: UploadFile,
    current_user: User = Depends(AuthService.get_current_user)
):
    """
    Upload an image for blog posts.
    This is a convenience endpoint that uses the main upload functionality.
    """
    from pathlib import Path
    import uuid
    import os

    # Validate file type
    allowed_types = {"image/jpeg", "image/jpg", "image/png", "image/gif", "image/webp"}
    if file.content_type not in allowed_types:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid file type. Allowed types: {', '.join(allowed_types)}"
        )

    # Read file content to check size
    contents = await file.read()
    file_size = len(contents)

    # Validate file size (10MB max)
    max_size = 10 * 1024 * 1024
    if file_size > max_size:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"File too large. Maximum size: {max_size / (1024 * 1024)} MB"
        )

    # Generate unique filename
    unique_filename = f"{uuid.uuid4()}{Path(file.filename).suffix}"
    file_path = Path("uploads") / "blog" / unique_filename

    # Ensure directory exists
    file_path.parent.mkdir(parents=True, exist_ok=True)

    # Save file
    with open(file_path, "wb") as f:
        f.write(contents)

    # Return file URL
    file_url = f"/uploads/blog/{unique_filename}"
    return {
        "success": True,
        "file_url": file_url,
        "filename": unique_filename,
        "original_filename": file.filename,
        "size": file_size
    }
