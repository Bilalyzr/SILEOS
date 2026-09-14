"""
Clear demo/fake data from database and optionally add real users
"""
import sqlite3
import sys

db_path = "test.db"

def clear_demo_data():
    """Clear all demo users and related data, keeping only admin"""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    try:
        print("=== CURRENT USERS ===")
        cursor.execute('SELECT id, user_login, display_name, user_email, role FROM users')
        users = cursor.fetchall()
        for user in users:
            print(f"ID: {user[0]}, Login: {user[1]}, Name: {user[2]}, Email: {user[3]}, Role: {user[4]}")

        print("\n=== CLEARING DEMO DATA ===")

        # Get demo user IDs (exclude admin with ID 1)
        demo_user_ids = [user[0] for user in users if user[0] != 1]

        if not demo_user_ids:
            print("No demo users to delete")
            return

        print(f"Will delete {len(demo_user_ids)} demo users: {demo_user_ids}")

        # Delete in correct order due to foreign keys
        for user_id in demo_user_ids:
            # Delete user-related data
            cursor.execute('DELETE FROM lesson_progress WHERE enrollment_id IN (SELECT id FROM enrollments WHERE user_id = ?)', (user_id,))
            cursor.execute('DELETE FROM student_course_activities WHERE user_id = ?', (user_id,))
            cursor.execute('DELETE FROM enrollments WHERE user_id = ?', (user_id,))
            cursor.execute('DELETE FROM quiz_attempts WHERE user_id = ?', (user_id,))
            cursor.execute('DELETE FROM order_items WHERE order_id IN (SELECT id FROM orders WHERE user_id = ?)', (user_id,))
            cursor.execute('DELETE FROM payments WHERE order_id IN (SELECT id FROM orders WHERE user_id = ?)', (user_id,))
            cursor.execute('DELETE FROM orders WHERE user_id = ?', (user_id,))
            cursor.execute('DELETE FROM earnings WHERE user_id = ?', (user_id,))
            cursor.execute('DELETE FROM withdrawals WHERE user_id = ?', (user_id,))
            cursor.execute('DELETE FROM issued_certificates WHERE user_id = ?', (user_id,))
            cursor.execute('DELETE FROM user_profiles WHERE user_id = ?', (user_id,))
            cursor.execute('DELETE FROM instructor_profiles WHERE user_id = ?', (user_id,))
            cursor.execute('DELETE FROM users WHERE id = ?', (user_id,))
            print(f"  Deleted user ID {user_id}")

        # Also clear demo courses
        print("\nClearing demo courses...")
        cursor.execute('DELETE FROM course_reviews')
        cursor.execute('DELETE FROM lesson_progress')
        cursor.execute('DELETE FROM enrollments')
        cursor.execute('DELETE FROM quiz_attempt_answers')
        cursor.execute('DELETE FROM quiz_attempts')
        cursor.execute('DELETE FROM quiz_question_answers')
        cursor.execute('DELETE FROM quiz_questions')
        cursor.execute('DELETE FROM quizzes')
        cursor.execute('DELETE FROM lessons')
        cursor.execute('DELETE FROM course_category_relations')
        cursor.execute('DELETE FROM course_tag_relations')
        cursor.execute('DELETE FROM courses')
        print("  Deleted all demo courses and related data")

        conn.commit()

        print("\n=== REMAINING USERS ===")
        cursor.execute('SELECT id, user_login, display_name, user_email, role FROM users')
        remaining = cursor.fetchall()
        for user in remaining:
            print(f"ID: {user[0]}, Login: {user[1]}, Name: {user[2]}, Email: {user[3]}, Role: {user[4]}")

        print("\n✓ Demo data cleared successfully!")
        print("✓ Database now contains only the admin user")
        print("\nYou can now:")
        print("1. Register real users through the frontend")
        print("2. Create real courses through the admin panel")

    except Exception as e:
        print(f"\n✗ Error: {e}")
        conn.rollback()
    finally:
        conn.close()

if __name__ == "__main__":
    print("This will delete ALL demo users and courses from the database.")
    print("Only the admin user will be kept.")

    confirm = input("\nAre you sure you want to continue? (yes/no): ")
    if confirm.lower() == 'yes':
        clear_demo_data()
    else:
        print("Operation cancelled")
