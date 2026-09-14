"""
Database Seed Data - Populate database with sample data for testing
Creates realistic SashaInfinity LMS data for demonstration and testing
"""

import asyncio
from sqlalchemy.orm import Session
from datetime import datetime, timedelta
import json

from app.core.database import SessionLocal, init_db, create_tables
from app.core.config import get_settings
from app.core.security import get_password_hash

# Import all models
from app.models.user import User, UserProfile, InstructorProfile
from app.models.course import Course, Lesson, CourseCategory, CourseTag
from app.models.quiz import Quiz, QuizQuestion, QuizQuestionAnswer
from app.models.enrollment import Enrollment, LessonProgress, StudentCourseActivity
from app.models.payment import Order, OrderItem, Payment
from app.models.certificate import Certificate, IssuedCertificate

settings = get_settings()

class DataSeeder:
    """Database seeder class"""

    def __init__(self):
        self.db = SessionLocal()

    def create_users(self):
        """Create sample users"""
        print("Creating sample users...")

        # Admin user
        admin = User(
            user_login="admin",
            user_pass=get_password_hash("admin123"),
            user_nicename="admin",
            user_email="admin@sashainfinity.com",
            display_name="System Administrator",
            is_active=True,
            is_verified=True
        )
        self.db.add(admin)

        # Instructor users
        instructor1 = User(
            user_login="john_instructor",
            user_pass=get_password_hash("instructor123"),
            user_nicename="john-instructor",
            user_email="john@sashainfinity.com",
            display_name="John Smith",
            is_active=True,
            is_verified=True
        )
        self.db.add(instructor1)

        instructor2 = User(
            user_login="sarah_instructor",
            user_pass=get_password_hash("instructor123"),
            user_nicename="sarah-instructor",
            user_email="sarah@sashainfinity.com",
            display_name="Sarah Johnson",
            is_active=True,
            is_verified=True
        )
        self.db.add(instructor2)

        # Student users
        students = [
            ("alice_student", "alice@example.com", "Alice Williams"),
            ("bob_student", "bob@example.com", "Bob Davis"),
            ("carol_student", "carol@example.com", "Carol Brown"),
            ("david_student", "david@example.com", "David Wilson"),
            ("emma_student", "emma@example.com", "Emma Taylor")
        ]

        for username, email, name in students:
            student = User(
                user_login=username,
                user_pass=get_password_hash("student123"),
                user_nicename=username.replace('_', '-'),
                user_email=email,
                display_name=name,
                is_active=True,
                is_verified=True
            )
            self.db.add(student)

        self.db.commit()
        print("Created 8 users (1 admin, 2 instructors, 5 students)")

    def create_categories_and_tags(self):
        """Create course categories and tags"""
        print("Creating categories and tags...")

        categories = [
            ("Programming", "programming", "Learn programming languages and frameworks"),
            ("Web Development", "web-development", "Build websites and web applications"),
            ("Data Science", "data-science", "Analyze data and build ML models"),
            ("Design", "design", "UI/UX design and graphic design"),
            ("Business", "business", "Business skills and entrepreneurship"),
            ("Marketing", "marketing", "Digital marketing and growth strategies")
        ]

        for name, slug, description in categories:
            category = CourseCategory(
                name=name,
                slug=slug,
                description=description
            )
            self.db.add(category)

        tags = [
            ("Python", "python"),
            ("JavaScript", "javascript"),
            ("React", "react"),
            ("Machine Learning", "machine-learning"),
            ("Beginner", "beginner"),
            ("Advanced", "advanced"),
            ("Project-Based", "project-based"),
            ("Certification", "certification")
        ]

        for name, slug in tags:
            tag = CourseTag(name=name, slug=slug)
            self.db.add(tag)

        self.db.commit()
        print("Created 6 categories and 8 tags")

    def create_courses(self):
        """Create sample courses"""
        print("Creating sample courses...")

        # Get instructors
        john = self.db.query(User).filter(User.user_login == "john_instructor").first()
        sarah = self.db.query(User).filter(User.user_login == "sarah_instructor").first()

        courses_data = [
            {
                "title": "Python Programming for Beginners",
                "description": "Learn Python from scratch with hands-on projects and real-world examples. Perfect for complete beginners.",
                "content": "This comprehensive course covers Python basics, data structures, functions, object-oriented programming, and more.",
                "excerpt": "Master Python programming from zero to hero",
                "price": 999.00,
                "level": "beginner",
                "category": "programming",
                "instructor": john,
                "duration": "8 weeks",
                "language": "English",
                "requirements": ["Basic computer skills", "No programming experience required"],
                "benefits": ["Learn Python fundamentals", "Build real projects", "Get certificate", "Lifetime access"]
            },
            {
                "title": "React.js Masterclass - Build Modern Web Apps",
                "description": "Master React.js and build production-ready web applications with hooks, context, and modern patterns.",
                "content": "Learn React from basics to advanced concepts including hooks, context API, routing, and state management.",
                "excerpt": "Build modern web applications with React.js",
                "price": 1499.00,
                "level": "intermediate",
                "category": "web-development",
                "instructor": john,
                "duration": "10 weeks",
                "language": "English",
                "requirements": ["Basic JavaScript knowledge", "HTML/CSS fundamentals"],
                "benefits": ["Master React hooks", "Build portfolio projects", "Learn best practices", "Job-ready skills"]
            },
            {
                "title": "Data Science with Python and Pandas",
                "description": "Learn data analysis, visualization, and machine learning with Python, Pandas, and Scikit-learn.",
                "content": "Complete data science workflow from data collection to model deployment using Python ecosystem.",
                "excerpt": "Become a data scientist with Python",
                "price": 1999.00,
                "level": "intermediate",
                "category": "data-science",
                "instructor": sarah,
                "duration": "12 weeks",
                "language": "English",
                "requirements": ["Python basics", "Statistics fundamentals"],
                "benefits": ["Master data analysis", "Build ML models", "Real datasets", "Industry projects"]
            },
            {
                "title": "UI/UX Design Fundamentals",
                "description": "Learn user interface and user experience design principles, tools, and best practices.",
                "content": "Complete guide to UI/UX design covering research, wireframing, prototyping, and design systems.",
                "excerpt": "Design beautiful and user-friendly interfaces",
                "price": 799.00,
                "level": "beginner",
                "category": "design",
                "instructor": sarah,
                "duration": "6 weeks",
                "language": "English",
                "requirements": ["Creative mindset", "Basic computer skills"],
                "benefits": ["Design thinking", "Figma mastery", "Portfolio building", "Design critique"]
            },
            {
                "title": "Free JavaScript Crash Course",
                "description": "Quick introduction to JavaScript fundamentals. Perfect for getting started with web development.",
                "content": "Learn JavaScript basics including variables, functions, DOM manipulation, and event handling.",
                "excerpt": "Start your JavaScript journey",
                "price": 0.00,
                "level": "beginner",
                "category": "programming",
                "instructor": john,
                "duration": "2 weeks",
                "language": "English",
                "requirements": ["Basic HTML knowledge"],
                "benefits": ["JavaScript basics", "DOM manipulation", "Interactive websites", "Foundation skills"]
            }
        ]

        for course_data in courses_data:
            course = Course(
                post_author=course_data["instructor"].id,
                post_title=course_data["title"],
                post_content=course_data["content"],
                post_excerpt=course_data["excerpt"],
                post_status="publish",
                post_name=course_data["title"].lower().replace(" ", "-").replace(".", ""),
                course_price=course_data["price"],
                course_level=course_data["level"],
                course_duration=course_data["duration"],
                course_benefits=json.dumps(course_data["benefits"]),
                course_requirements=json.dumps(course_data["requirements"]),
                total_enrollments=0,
                average_rating=0.0,
                total_reviews=0
            )
            self.db.add(course)

        self.db.commit()
        print("Created 5 courses (4 paid, 1 free)")

    def create_lessons(self):
        """Create sample lessons for courses"""
        print("Creating sample lessons...")

        # Get courses
        courses = self.db.query(Course).all()

        lesson_data = {
            "Python Programming for Beginners": [
                ("Introduction to Python", "Welcome to Python programming", "https://example.com/video1", "600"),
                ("Variables and Data Types", "Learn about Python data types", "https://example.com/video2", "900"),
                ("Control Structures", "If statements and loops", "https://example.com/video3", "1200"),
                ("Functions", "Writing reusable code", "https://example.com/video4", "1500"),
                ("Lists and Dictionaries", "Working with data structures", "https://example.com/video5", "1800")
            ],
            "React.js Masterclass - Build Modern Web Apps": [
                ("React Fundamentals", "Components, JSX, and Props", "https://example.com/react1", "1200"),
                ("State and Events", "Managing component state", "https://example.com/react2", "1500"),
                ("React Hooks", "useState, useEffect, and more", "https://example.com/react3", "1800"),
                ("Routing", "React Router for navigation", "https://example.com/react4", "1200"),
                ("State Management", "Context API and Redux", "https://example.com/react5", "2100")
            ],
            "Free JavaScript Crash Course": [
                ("JavaScript Basics", "Variables and functions", "https://example.com/js1", "600"),
                ("DOM Manipulation", "Interacting with web pages", "https://example.com/js2", "900"),
                ("Event Handling", "Responding to user actions", "https://example.com/js3", "800")
            ]
        }

        lesson_count = 0
        for course in courses:
            if course.post_title in lesson_data:
                lessons = lesson_data[course.post_title]
                for i, (title, content, video_url, duration) in enumerate(lessons):
                    lesson = Lesson(
                        post_author=course.post_author,
                        post_title=title,
                        post_content=content,
                        post_status="publish",
                        post_name=title.lower().replace(" ", "-"),
                        post_parent=course.id,
                        menu_order=i + 1,
                        lesson_video_url=video_url,
                        lesson_video_duration=duration,
                        lesson_preview=(i == 0)  # First lesson is preview
                    )
                    self.db.add(lesson)
                    lesson_count += 1

        self.db.commit()
        print(f"Created {lesson_count} lessons")

    def create_enrollments(self):
        """Create sample enrollments"""
        print("Creating sample enrollments...")

        # Get students and courses
        students = self.db.query(User).filter(User.user_login.like("%student%")).all()
        courses = self.db.query(Course).all()

        enrollment_count = 0
        for student in students:
            # Each student enrolls in 2-3 random courses
            import random
            enrolled_courses = random.sample(courses, random.randint(2, 3))

            for course in enrolled_courses:
                enrollment = Enrollment(
                    course_id=course.id,
                    user_id=student.id,
                    enrollment_status="enrolled",
                    course_progress_percentage=random.randint(0, 100),
                    completed_lessons=0,
                    total_lessons=3,  # Simplified
                    enrollment_date=datetime.utcnow() - timedelta(days=random.randint(1, 30))
                )
                self.db.add(enrollment)
                enrollment_count += 1

                # Update course enrollment count
                course.total_enrollments = (course.total_enrollments or 0) + 1

        self.db.commit()
        print(f"Created {enrollment_count} enrollments")

    def create_sample_orders(self):
        """Create sample orders for paid courses"""
        print("Creating sample orders...")

        # Get paid courses and students
        paid_courses = self.db.query(Course).filter(Course.course_price > 0).all()
        students = self.db.query(User).filter(User.user_login.like("%student%")).all()

        order_count = 0
        for i, course in enumerate(paid_courses[:3]):  # Create orders for first 3 paid courses
            student = students[i % len(students)]

            order = Order(
                user_id=student.id,
                order_key=f"order_{order_count + 1:04d}",
                order_status="completed",
                currency="INR",
                total_amount=course.course_price,
                subtotal_amount=course.course_price,
                payment_method="razorpay",
                payment_method_title="Razorpay",
                billing_first_name=student.display_name.split()[0],
                billing_last_name=student.display_name.split()[-1],
                billing_email=student.user_email,
                date_created=datetime.utcnow() - timedelta(days=i + 1),
                date_paid=datetime.utcnow() - timedelta(days=i + 1)
            )
            self.db.add(order)
            self.db.flush()

            # Create order item
            order_item = OrderItem(
                order_id=order.id,
                course_id=course.id,
                course_title=course.post_title,
                course_price=course.course_price,
                quantity=1
            )
            self.db.add(order_item)
            order_count += 1

        self.db.commit()
        print(f"Created {order_count} sample orders")

    def seed_all(self):
        """Run all seed methods"""
        print("Starting database seeding...")
        print("=" * 50)

        try:
            self.create_users()
            self.create_categories_and_tags()
            self.create_courses()
            self.create_lessons()
            self.create_enrollments()
            self.create_sample_orders()

            print("=" * 50)
            print("Database seeding completed successfully!")
            print("\nSummary:")
            print(f"   • Users: {self.db.query(User).count()}")
            print(f"   • Courses: {self.db.query(Course).count()}")
            print(f"   • Lessons: {self.db.query(Lesson).count()}")
            print(f"   • Categories: {self.db.query(CourseCategory).count()}")
            print(f"   • Tags: {self.db.query(CourseTag).count()}")
            print(f"   • Enrollments: {self.db.query(Enrollment).count()}")
            print(f"   • Orders: {self.db.query(Order).count()}")

        except Exception as e:
            print(f"Error during seeding: {e}")
            self.db.rollback()
        finally:
            self.db.close()

async def main():
    """Main function"""
    # Initialize database and create tables
    await init_db()
    create_tables()

    # Seed data
    seeder = DataSeeder()
    seeder.seed_all()

if __name__ == "__main__":
    asyncio.run(main())