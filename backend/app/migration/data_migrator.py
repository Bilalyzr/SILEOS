#!/usr/bin/env python3
"""
Data Migrator - Migrate extracted legacy data to PostgreSQL
This script takes the JSON data extracted from legacy systems and migrates it to PostgreSQL
"""
import json
import asyncio
import asyncpg
from datetime import datetime
from typing import Dict, List, Any, Optional
import argparse
import os
import hashlib
import uuid
from decimal import Decimal

class DataMigrator:
    def __init__(self, postgres_url: str):
        """Initialize data migrator with PostgreSQL connection"""
        self.postgres_url = postgres_url
        self.connection = None
        self.data = {}
        self.migration_stats = {
            'users': 0,
            'courses': 0,
            'lessons': 0,
            'quizzes': 0,
            'enrollments': 0,
            'orders': 0,
            'certificates': 0,
            'errors': []
        }

    async def connect(self):
        """Connect to PostgreSQL database"""
        try:
            self.connection = await asyncpg.connect(self.postgres_url)
            print("✅ Connected to PostgreSQL database successfully!")
            return True
        except Exception as e:
            print(f"❌ Error connecting to PostgreSQL: {e}")
            return False

    def load_data(self, json_file: str) -> bool:
        """Load extracted legacy data from JSON file"""
        try:
            with open(json_file, 'r', encoding='utf-8') as f:
                self.data = json.load(f)

            print(f"✅ Loaded legacy data from {json_file}")
            print(f"   Users: {len(self.data.get('users', []))}")
            print(f"   Courses: {len(self.data.get('courses', []))}")
            print(f"   Lessons: {len(self.data.get('lessons', []))}")
            print(f"   Quizzes: {len(self.data.get('quizzes', []))}")
            print(f"   Enrollments: {len(self.data.get('enrollments', []))}")
            print(f"   Orders: {len(self.data.get('orders', []))}")
            return True
        except Exception as e:
            print(f"❌ Error loading data: {e}")
            return False

    def convert_datetime(self, wp_datetime: str) -> Optional[str]:
        """Convert legacy datetime to PostgreSQL format"""
        if not wp_datetime or wp_datetime == '0000-00-00 00:00:00':
            return None

        try:
            # Parse legacy datetime
            dt = datetime.strptime(wp_datetime, '%Y-%m-%d %H:%M:%S')
            return dt.isoformat()
        except ValueError:
            return None

    def generate_unique_key(self, prefix: str = "") -> str:
        """Generate unique key for orders etc."""
        return f"{prefix}{uuid.uuid4().hex[:12]}"

    async def migrate_users(self):
        """Migrate users from legacy to PostgreSQL"""
        print("👤 Migrating users...")

        users = self.data.get('users', [])
        migrated_count = 0

        for wp_user in users:
            try:
                meta = wp_user.get('meta_data', {})

                # Insert user
                await self.connection.execute("""
                    INSERT INTO users (
                        id, user_login, user_pass, user_nicename, user_email,
                        user_url, user_registered, user_activation_key, user_status,
                        display_name, is_active, is_verified, created_at, updated_at
                    ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14)
                    ON CONFLICT (id) DO NOTHING
                """,
                    wp_user['ID'],
                    wp_user['user_login'],
                    wp_user['user_pass'],
                    wp_user['user_nicename'],
                    wp_user['user_email'],
                    wp_user.get('user_url', ''),
                    self.convert_datetime(wp_user.get('user_registered')),
                    wp_user.get('user_activation_key', ''),
                    wp_user.get('user_status', 0),
                    wp_user['display_name'],
                    True,  # is_active
                    True,  # is_verified
                    self.convert_datetime(wp_user.get('user_registered')),
                    datetime.now().isoformat()
                )

                # Insert user profile
                await self.connection.execute("""
                    INSERT INTO user_profiles (
                        user_id, first_name, last_name, description, phone,
                        designation, address, city, state, country, postal_code,
                        profile_photo, cover_photo, facebook, twitter, linkedin,
                        website, show_email, receive_notifications, created_at, updated_at
                    ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14, $15, $16, $17, $18, $19, $20, $21)
                    ON CONFLICT (user_id) DO NOTHING
                """,
                    wp_user['ID'],
                    meta.get('first_name', ''),
                    meta.get('last_name', ''),
                    meta.get('description', ''),
                    meta.get('phone', ''),
                    meta.get('designation', ''),
                    meta.get('address', ''),
                    meta.get('city', ''),
                    meta.get('state', ''),
                    meta.get('country', ''),
                    meta.get('postal_code', ''),
                    meta.get('profile_photo', ''),
                    meta.get('cover_photo', ''),
                    meta.get('facebook', ''),
                    meta.get('twitter', ''),
                    meta.get('linkedin', ''),
                    meta.get('website', ''),
                    meta.get('show_email', 'false') == 'true',
                    meta.get('receive_notifications', 'true') == 'true',
                    datetime.now().isoformat(),
                    datetime.now().isoformat()
                )

                # Insert instructor profile if user is instructor
                if '_tutor_instructor_status' in meta and meta['_tutor_instructor_status'] == 'approved':
                    await self.connection.execute("""
                        INSERT INTO instructor_profiles (
                            user_id, instructor_rating, instructor_bio, instructor_designation,
                            profile_completion, is_approved, is_blocked, earning_commission_type,
                            earning_commission_amount, created_at, updated_at
                        ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11)
                        ON CONFLICT (user_id) DO NOTHING
                    """,
                        wp_user['ID'],
                        meta.get('_tutor_instructor_rating', '0'),
                        meta.get('_tutor_profile_bio', ''),
                        meta.get('_tutor_profile_job_title', ''),
                        int(meta.get('_tutor_profile_completion', '0')),
                        True,
                        False,
                        'percentage',
                        meta.get('_tutor_instructor_commission_rate', '80'),
                        datetime.now().isoformat(),
                        datetime.now().isoformat()
                    )

                migrated_count += 1

            except Exception as e:
                error_msg = f"Error migrating user {wp_user.get('ID', 'unknown')}: {e}"
                print(f"   ⚠️ {error_msg}")
                self.migration_stats['errors'].append(error_msg)

        self.migration_stats['users'] = migrated_count
        print(f"   ✅ Migrated {migrated_count} users")

    async def migrate_courses(self):
        """Migrate courses from legacy to PostgreSQL"""
        print("📚 Migrating courses...")

        courses = self.data.get('courses', [])
        migrated_count = 0

        for wp_course in courses:
            try:
                meta = wp_course.get('meta_data', {})

                await self.connection.execute("""
                    INSERT INTO courses (
                        id, post_author, post_date, post_date_gmt, post_content,
                        post_title, post_excerpt, post_status, comment_status,
                        ping_status, post_password, post_name, to_ping, pinged,
                        post_modified, post_modified_gmt, post_content_filtered,
                        post_parent, guid, menu_order, post_type, post_mime_type,
                        comment_count, course_price_type, course_price, course_sale_price,
                        course_duration, course_level, course_benefits, course_requirements,
                        course_target_audience, course_material_includes, course_thumbnail,
                        course_cover_image, course_intro_video, course_retakes_allowed,
                        course_auto_start_next_lesson, course_content_drip_type,
                        certificate_template, total_enrollments, average_rating,
                        total_reviews, created_at, updated_at
                    ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14, $15, $16, $17, $18, $19, $20, $21, $22, $23, $24, $25, $26, $27, $28, $29, $30, $31, $32, $33, $34, $35, $36, $37, $38, $39, $40, $41, $42, $43, $44)
                    ON CONFLICT (id) DO NOTHING
                """,
                    wp_course['ID'],
                    wp_course['post_author'],
                    self.convert_datetime(wp_course.get('post_date')),
                    self.convert_datetime(wp_course.get('post_date_gmt')),
                    wp_course.get('post_content', ''),
                    wp_course['post_title'],
                    wp_course.get('post_excerpt', ''),
                    wp_course.get('post_status', 'draft'),
                    wp_course.get('comment_status', 'open'),
                    wp_course.get('ping_status', 'open'),
                    wp_course.get('post_password', ''),
                    wp_course.get('post_name', ''),
                    wp_course.get('to_ping', ''),
                    wp_course.get('pinged', ''),
                    self.convert_datetime(wp_course.get('post_modified')),
                    self.convert_datetime(wp_course.get('post_modified_gmt')),
                    wp_course.get('post_content_filtered', ''),
                    wp_course.get('post_parent', 0),
                    wp_course.get('guid', ''),
                    wp_course.get('menu_order', 0),
                    'courses',
                    wp_course.get('post_mime_type', ''),
                    wp_course.get('comment_count', 0),
                    meta.get('_tutor_course_price_type', 'free'),
                    Decimal(meta.get('_regular_price', '0')),
                    Decimal(meta.get('_sale_price', '0')),
                    meta.get('_course_duration', ''),
                    meta.get('_tutor_course_level', 'beginner'),
                    meta.get('_tutor_course_benefits', ''),
                    meta.get('_tutor_course_requirements', ''),
                    meta.get('_tutor_course_target_audience', ''),
                    meta.get('_tutor_course_material_includes', ''),
                    meta.get('_thumbnail_id', ''),
                    meta.get('_course_cover_image', ''),
                    meta.get('_video', ''),
                    meta.get('_tutor_course_settings', {}).get('course_retake', True),
                    False,
                    meta.get('_tutor_course_settings', {}).get('content_drip_type', 'none'),
                    meta.get('_tutor_certificate_template', ''),
                    int(meta.get('_course_total_enrolled', '0')),
                    Decimal(meta.get('_tutor_course_avg_rating', '0')),
                    int(meta.get('_tutor_course_total_rating', '0')),
                    datetime.now().isoformat(),
                    datetime.now().isoformat()
                )

                migrated_count += 1

            except Exception as e:
                error_msg = f"Error migrating course {wp_course.get('ID', 'unknown')}: {e}"
                print(f"   ⚠️ {error_msg}")
                self.migration_stats['errors'].append(error_msg)

        self.migration_stats['courses'] = migrated_count
        print(f"   ✅ Migrated {migrated_count} courses")

    async def migrate_lessons(self):
        """Migrate lessons from legacy to PostgreSQL"""
        print("📖 Migrating lessons...")

        lessons = self.data.get('lessons', [])
        migrated_count = 0

        for wp_lesson in lessons:
            try:
                meta = wp_lesson.get('meta_data', {})

                await self.connection.execute("""
                    INSERT INTO lessons (
                        id, post_author, post_date, post_content, post_title,
                        post_excerpt, post_status, post_name, post_modified,
                        post_parent, menu_order, post_type, lesson_video_source,
                        lesson_video_url, lesson_video_duration, lesson_video_poster,
                        lesson_attachments, lesson_preview, created_at, updated_at
                    ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14, $15, $16, $17, $18, $19, $20)
                    ON CONFLICT (id) DO NOTHING
                """,
                    wp_lesson['ID'],
                    wp_lesson['post_author'],
                    self.convert_datetime(wp_lesson.get('post_date')),
                    wp_lesson.get('post_content', ''),
                    wp_lesson['post_title'],
                    wp_lesson.get('post_excerpt', ''),
                    wp_lesson.get('post_status', 'publish'),
                    wp_lesson.get('post_name', ''),
                    self.convert_datetime(wp_lesson.get('post_modified')),
                    wp_lesson.get('post_parent', 0),
                    wp_lesson.get('menu_order', 0),
                    'lesson',
                    meta.get('_video_source', 'html5'),
                    meta.get('_video', ''),
                    meta.get('_video_duration', ''),
                    meta.get('_video_poster', ''),
                    meta.get('_lesson_attachments', ''),
                    meta.get('_lesson_preview', 'false') == 'true',
                    datetime.now().isoformat(),
                    datetime.now().isoformat()
                )

                migrated_count += 1

            except Exception as e:
                error_msg = f"Error migrating lesson {wp_lesson.get('ID', 'unknown')}: {e}"
                print(f"   ⚠️ {error_msg}")
                self.migration_stats['errors'].append(error_msg)

        self.migration_stats['lessons'] = migrated_count
        print(f"   ✅ Migrated {migrated_count} lessons")

    async def migrate_quizzes(self):
        """Migrate quizzes and related data"""
        print("📝 Migrating quizzes...")

        # Migrate quiz posts
        quizzes = self.data.get('quizzes', [])
        quiz_count = 0

        for wp_quiz in quizzes:
            try:
                meta = wp_quiz.get('meta_data', {})

                await self.connection.execute("""
                    INSERT INTO quizzes (
                        id, post_author, post_date, post_content, post_title,
                        post_excerpt, post_status, post_name, post_modified,
                        post_parent, menu_order, post_type, quiz_time_limit,
                        quiz_feedback_mode, quiz_max_questions_for_take,
                        quiz_max_attempts_allowed, quiz_passing_grade,
                        quiz_question_layout_view, quiz_questions_order,
                        quiz_hide_quiz_details, quiz_hide_quiz_time_display,
                        quiz_auto_start, created_at, updated_at
                    ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14, $15, $16, $17, $18, $19, $20, $21, $22, $23, $24)
                    ON CONFLICT (id) DO NOTHING
                """,
                    wp_quiz['ID'],
                    wp_quiz['post_author'],
                    self.convert_datetime(wp_quiz.get('post_date')),
                    wp_quiz.get('post_content', ''),
                    wp_quiz['post_title'],
                    wp_quiz.get('post_excerpt', ''),
                    wp_quiz.get('post_status', 'publish'),
                    wp_quiz.get('post_name', ''),
                    self.convert_datetime(wp_quiz.get('post_modified')),
                    wp_quiz.get('post_parent', 0),
                    wp_quiz.get('menu_order', 0),
                    'tutor_quiz',
                    int(meta.get('tutor_quiz_time_limit', '0')),
                    meta.get('tutor_quiz_feedback_mode', 'default'),
                    int(meta.get('tutor_quiz_max_questions_for_take', '10')),
                    int(meta.get('tutor_quiz_max_attempts_allowed', '0')),
                    int(meta.get('tutor_quiz_passing_grade', '80')),
                    meta.get('tutor_quiz_question_layout_view', 'single_question'),
                    meta.get('tutor_quiz_questions_order', 'rand'),
                    meta.get('tutor_quiz_hide_quiz_details', 'false') == 'true',
                    meta.get('tutor_quiz_hide_quiz_time_display', 'false') == 'true',
                    meta.get('tutor_quiz_auto_start', 'false') == 'true',
                    datetime.now().isoformat(),
                    datetime.now().isoformat()
                )
                quiz_count += 1
            except Exception as e:
                error_msg = f"Error migrating quiz {wp_quiz.get('ID', 'unknown')}: {e}"
                print(f"   ⚠️ {error_msg}")
                self.migration_stats['errors'].append(error_msg)

        # Migrate quiz questions
        questions = self.data.get('quiz_questions', [])
        question_count = 0

        for question in questions:
            try:
                await self.connection.execute("""
                    INSERT INTO quiz_questions (
                        question_id, quiz_id, question_title, question_description,
                        answer_explanation, question_type, question_mark,
                        question_settings, question_order, created_at, updated_at
                    ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11)
                    ON CONFLICT (question_id) DO NOTHING
                """,
                    question['question_id'],
                    question['quiz_id'],
                    question['question_title'],
                    question.get('question_description', ''),
                    question.get('answer_explanation', ''),
                    question['question_type'],
                    Decimal(str(question.get('question_mark', '1.0'))),
                    json.dumps(question.get('question_settings', {})),
                    question.get('question_order', 0),
                    datetime.now().isoformat(),
                    datetime.now().isoformat()
                )
                question_count += 1
            except Exception as e:
                error_msg = f"Error migrating question {question.get('question_id', 'unknown')}: {e}"
                print(f"   ⚠️ {error_msg}")
                self.migration_stats['errors'].append(error_msg)

        # Migrate quiz answers
        answers = self.data.get('quiz_answers', [])
        answer_count = 0

        for answer in answers:
            try:
                await self.connection.execute("""
                    INSERT INTO quiz_question_answers (
                        answer_id, belongs_question_id, belongs_question_type,
                        answer_title, is_correct, image_id, answer_two_gap_match,
                        answer_view_format, answer_settings, answer_order, created_at
                    ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11)
                    ON CONFLICT (answer_id) DO NOTHING
                """,
                    answer['answer_id'],
                    answer['belongs_question_id'],
                    answer.get('belongs_question_type', ''),
                    answer['answer_title'],
                    bool(answer.get('is_correct', 0)),
                    answer.get('image_id', 0),
                    answer.get('answer_two_gap_match', ''),
                    answer.get('answer_view_format', ''),
                    json.dumps(answer.get('answer_settings', {})),
                    answer.get('answer_order', 0),
                    datetime.now().isoformat()
                )
                answer_count += 1
            except Exception as e:
                error_msg = f"Error migrating answer {answer.get('answer_id', 'unknown')}: {e}"
                print(f"   ⚠️ {error_msg}")
                self.migration_stats['errors'].append(error_msg)

        self.migration_stats['quizzes'] = quiz_count
        print(f"   ✅ Migrated {quiz_count} quizzes, {question_count} questions, {answer_count} answers")

    async def migrate_enrollments(self):
        """Migrate enrollment data"""
        print("🎓 Migrating enrollments...")

        enrollments = self.data.get('enrollments', [])
        migrated_count = 0

        for enrollment in enrollments:
            try:
                await self.connection.execute("""
                    INSERT INTO enrollments (
                        id, course_id, user_id, order_id, enrollment_date,
                        enrollment_status, course_progress_percentage,
                        completed_lessons, total_lessons, completed_quizzes,
                        total_quizzes, completion_date, completion_mode,
                        completion_mode_text, created_at, updated_at
                    ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14, $15, $16)
                    ON CONFLICT (id) DO NOTHING
                """,
                    enrollment['enrollment_id'],
                    enrollment['course_id'],
                    enrollment['user_id'],
                    enrollment.get('order_id'),
                    self.convert_datetime(enrollment.get('enrollment_date_gmt')),
                    enrollment.get('enrollment_status', 'enrolled'),
                    int(enrollment.get('course_progress_percentage', 0)),
                    int(enrollment.get('completed_lessons', 0)),
                    int(enrollment.get('total_lessons', 0)),
                    int(enrollment.get('completed_quizzes', 0)),
                    int(enrollment.get('total_quizzes', 0)),
                    self.convert_datetime(enrollment.get('completion_date')),
                    enrollment.get('completion_mode', ''),
                    enrollment.get('completion_mode_text', ''),
                    datetime.now().isoformat(),
                    datetime.now().isoformat()
                )
                migrated_count += 1
            except Exception as e:
                error_msg = f"Error migrating enrollment {enrollment.get('enrollment_id', 'unknown')}: {e}"
                print(f"   ⚠️ {error_msg}")
                self.migration_stats['errors'].append(error_msg)

        self.migration_stats['enrollments'] = migrated_count
        print(f"   ✅ Migrated {migrated_count} enrollments")

    async def migrate_orders(self):
        """Migrate order and payment data"""
        print("💳 Migrating orders...")

        orders = self.data.get('orders', [])
        migrated_count = 0

        for order in orders:
            try:
                # Handle both wc_orders and wp_posts sources
                if self.data.get('order_source') == 'wc_orders':
                    order_id = order['id']
                    user_id = order['customer_id']
                    total = order.get('total', '0')
                    status = order.get('status', 'pending')
                    date_created = order.get('date_created_gmt')
                else:
                    order_id = order['ID']
                    user_id = order.get('post_author', 0)
                    total = '0'  # Would need to get from meta
                    status = order.get('post_status', 'pending')
                    date_created = order.get('post_date_gmt')

                await self.connection.execute("""
                    INSERT INTO orders (
                        id, user_id, order_key, order_status, currency,
                        total_amount, subtotal_amount, tax_amount,
                        shipping_amount, discount_amount, payment_method,
                        payment_method_title, transaction_id, date_created,
                        date_modified, created_at, updated_at
                    ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14, $15, $16, $17)
                    ON CONFLICT (id) DO NOTHING
                """,
                    order_id,
                    user_id,
                    self.generate_unique_key("wc_order_"),
                    status,
                    'INR',
                    Decimal(str(total)),
                    Decimal(str(total)),
                    Decimal('0'),
                    Decimal('0'),
                    Decimal('0'),
                    'razorpay',
                    'Razorpay',
                    '',
                    self.convert_datetime(date_created),
                    datetime.now().isoformat(),
                    datetime.now().isoformat(),
                    datetime.now().isoformat()
                )
                migrated_count += 1
            except Exception as e:
                error_msg = f"Error migrating order {order.get('id', order.get('ID', 'unknown'))}: {e}"
                print(f"   ⚠️ {error_msg}")
                self.migration_stats['errors'].append(error_msg)

        self.migration_stats['orders'] = migrated_count
        print(f"   ✅ Migrated {migrated_count} orders")

    async def migrate_all_data(self):
        """Migrate all data to PostgreSQL"""
        if not await self.connect():
            return False

        print("🚀 Starting PostgreSQL data migration...")

        try:
            # Migrate in dependency order
            await self.migrate_users()
            await self.migrate_courses()
            await self.migrate_lessons()
            await self.migrate_quizzes()
            await self.migrate_enrollments()
            await self.migrate_orders()

            # Print migration summary
            print("\n📊 Migration Summary:")
            print(f"   Users: {self.migration_stats['users']}")
            print(f"   Courses: {self.migration_stats['courses']}")
            print(f"   Lessons: {self.migration_stats['lessons']}")
            print(f"   Quizzes: {self.migration_stats['quizzes']}")
            print(f"   Enrollments: {self.migration_stats['enrollments']}")
            print(f"   Orders: {self.migration_stats['orders']}")

            if self.migration_stats['errors']:
                print(f"\n⚠️ Errors encountered: {len(self.migration_stats['errors'])}")
                for error in self.migration_stats['errors'][:5]:  # Show first 5 errors
                    print(f"   - {error}")

            print("✅ Data migration completed!")
            return True

        except Exception as e:
            print(f"❌ Migration failed: {e}")
            return False
        finally:
            if self.connection:
                await self.connection.close()

def main():
    parser = argparse.ArgumentParser(description='Migrate legacy data to PostgreSQL')
    parser.add_argument('json_file', help='JSON file with extracted legacy data')
    parser.add_argument('postgres_url', help='PostgreSQL connection URL')

    args = parser.parse_args()

    # Run migration
    migrator = DataMigrator(args.postgres_url)
    if migrator.load_data(args.json_file):
        asyncio.run(migrator.migrate_all_data())
    else:
        print("❌ Failed to load legacy data")

if __name__ == "__main__":
    main()