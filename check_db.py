import sqlite3

conn = sqlite3.connect('test.db')
cursor = conn.cursor()

print("=== COURSES IN DATABASE ===")
cursor.execute('SELECT id, post_title, total_enrollments, average_rating, course_price FROM courses LIMIT 5')
for row in cursor.fetchall():
    print(f'ID: {row[0]}, Title: {row[1]}, Enrollments: {row[2]}, Rating: {row[3]}, Price: {row[4]}')

print("\n=== USERS IN DATABASE ===")
cursor.execute('SELECT id, display_name, user_email, role FROM users LIMIT 5')
for row in cursor.fetchall():
    print(f'ID: {row[0]}, Name: {row[1]}, Email: {row[2]}, Role: {row[3]}')

print("\n=== ENROLLMENTS IN DATABASE ===")
cursor.execute('SELECT id, user_id, course_id, enrollment_status FROM enrollments LIMIT 5')
for row in cursor.fetchall():
    print(f'ID: {row[0]}, Student: {row[1]}, Course: {row[2]}, Status: {row[3]}')

conn.close()
