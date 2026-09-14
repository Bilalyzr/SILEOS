"""
Script to delete all courses and related data from the database
Run this from the backend directory: python -m app.scripts.delete_all_courses
"""

import sys
import os
from pathlib import Path

# Add the parent directory to the path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from sqlalchemy.orm import Session
from app.core.database import SessionLocal
from app.models.course import Course, Lesson, CourseCategory, CourseTag
from app.models.quiz import Quiz, QuizQuestion, QuizAttempt, QuizAnswer
from app.models.enrollment import Enrollment
from app.models.payment import Order, OrderItem, Payment

def delete_all_courses():
    """Delete all courses and their related data"""
    db = SessionLocal()

    try:
        print("Starting deletion of all courses and related data...")
        print("=" * 60)

        # Get count before deletion
        course_count = db.query(Course).count()
        print(f"\nFound {course_count} courses to delete")

        if course_count == 0:
            print("No courses found in database.")
            return

        # Confirm deletion
        confirm = input(f"\nAre you sure you want to delete ALL {course_count} courses? (yes/no): ")
        if confirm.lower() != 'yes':
            print("Deletion cancelled.")
            return

        # Delete in order to respect foreign key constraints

        # 1. Delete quiz answers
        quiz_answer_count = db.query(QuizAnswer).delete()
        print(f"✓ Deleted {quiz_answer_count} quiz answers")

        # 2. Delete quiz attempts
        quiz_attempt_count = db.query(QuizAttempt).delete()
        print(f"✓ Deleted {quiz_attempt_count} quiz attempts")

        # 3. Delete quiz questions
        quiz_question_count = db.query(QuizQuestion).delete()
        print(f"✓ Deleted {quiz_question_count} quiz questions")

        # 4. Delete quizzes
        quiz_count = db.query(Quiz).delete()
        print(f"✓ Deleted {quiz_count} quizzes")

        # 5. Delete enrollments
        enrollment_count = db.query(Enrollment).delete()
        print(f"✓ Deleted {enrollment_count} enrollments")

        # 6. Delete payments
        payment_count = db.query(Payment).delete()
        print(f"✓ Deleted {payment_count} payments")

        # 7. Delete order items
        order_item_count = db.query(OrderItem).delete()
        print(f"✓ Deleted {order_item_count} order items")

        # 8. Delete orders
        order_count = db.query(Order).delete()
        print(f"✓ Deleted {order_count} orders")

        # 9. Delete lessons
        lesson_count = db.query(Lesson).delete()
        print(f"✓ Deleted {lesson_count} lessons")

        # 10. Delete course categories (associations)
        category_assoc_count = db.query(CourseCategory).delete()
        print(f"✓ Deleted {category_assoc_count} course-category associations")

        # 11. Delete course tags (associations)
        tag_assoc_count = db.query(CourseTag).delete()
        print(f"✓ Deleted {tag_assoc_count} course-tag associations")

        # 12. Finally, delete courses
        deleted_courses = db.query(Course).delete()
        print(f"✓ Deleted {deleted_courses} courses")

        # Commit the transaction
        db.commit()

        print("\n" + "=" * 60)
        print("✅ Successfully deleted all courses and related data!")
        print("=" * 60)

        # Also try to clean up uploaded files
        print("\nCleaning up uploaded files...")
        uploads_dir = Path("/app/uploads")
        if uploads_dir.exists():
            # Delete images
            images_dir = uploads_dir / "images"
            if images_dir.exists():
                image_files = list(images_dir.glob("*"))
                for f in image_files:
                    if f.is_file():
                        f.unlink()
                print(f"✓ Deleted {len(image_files)} image files")

            # Delete videos
            videos_dir = uploads_dir / "videos"
            if videos_dir.exists():
                video_files = list(videos_dir.glob("*"))
                for f in video_files:
                    if f.is_file():
                        f.unlink()
                print(f"✓ Deleted {len(video_files)} video files")

            # Delete documents
            documents_dir = uploads_dir / "documents"
            if documents_dir.exists():
                document_files = list(documents_dir.glob("*"))
                for f in document_files:
                    if f.is_file():
                        f.unlink()
                print(f"✓ Deleted {len(document_files)} document files")

            # Clean temp directory
            temp_dir = uploads_dir / "temp"
            if temp_dir.exists():
                import shutil
                shutil.rmtree(temp_dir)
                print(f"✓ Cleaned temporary upload directory")

        print("\n✅ Database and file cleanup complete!")

    except Exception as e:
        db.rollback()
        print(f"\n❌ Error during deletion: {str(e)}")
        import traceback
        traceback.print_exc()
    finally:
        db.close()


if __name__ == "__main__":
    delete_all_courses()
