"""
Fix database schema by adding missing course_category column
"""
import sqlite3
import os

db_path = "test.db"

if not os.path.exists(db_path):
    print(f"Database {db_path} not found!")
    exit(1)

conn = sqlite3.connect(db_path)
cursor = conn.cursor()

try:
    # Check if course_category column exists
    cursor.execute("PRAGMA table_info(courses)")
    columns = [row[1] for row in cursor.fetchall()]

    if 'course_category' not in columns:
        print("Adding course_category column...")
        cursor.execute("ALTER TABLE courses ADD COLUMN course_category VARCHAR(100) DEFAULT ''")
        conn.commit()
        print("Successfully added course_category column")
    else:
        print("course_category column already exists")

    # Verify the fix
    cursor.execute("PRAGMA table_info(courses)")
    columns = [row[1] for row in cursor.fetchall()]
    print(f"\nCourses table now has {len(columns)} columns")
    print(f"course_category present: {'course_category' in columns}")

except Exception as e:
    print(f"Error: {e}")
    conn.rollback()
finally:
    conn.close()

print("\nDatabase schema fix completed!")
