"""
Update admin user to real credentials
"""
import sqlite3
import sys
from app.core.security import get_password_hash

db_path = "test.db"

def update_admin(username, email, display_name, password):
    """Update admin user with real credentials"""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    try:
        print("=== CURRENT ADMIN USER ===")
        cursor.execute('SELECT id, user_login, display_name, user_email FROM users WHERE id = 1')
        admin = cursor.fetchone()
        print(f"ID: {admin[0]}, Login: {admin[1]}, Name: {admin[2]}, Email: {admin[3]}")

        print("\n=== UPDATING ADMIN USER ===")

        # Hash the password
        hashed_password = get_password_hash(password)

        # Update admin user
        cursor.execute('''
            UPDATE users
            SET user_login = ?,
                user_email = ?,
                display_name = ?,
                user_pass = ?,
                user_nicename = ?,
                role = 'admin'
            WHERE id = 1
        ''', (username, email, display_name, hashed_password, username.lower().replace(' ', '-')))

        conn.commit()

        print("\n=== UPDATED ADMIN USER ===")
        cursor.execute('SELECT id, user_login, display_name, user_email, role FROM users WHERE id = 1')
        admin = cursor.fetchone()
        print(f"ID: {admin[0]}, Login: {admin[1]}, Name: {admin[2]}, Email: {admin[3]}, Role: {admin[4]}")

        print("\n--- Admin user updated successfully!")
        print(f"Login: {username}")
        print(f"Password: {password}")
        print(f"Email: {email}")

    except Exception as e:
        print(f"\n--- Error: {e}")
        conn.rollback()
    finally:
        conn.close()

if __name__ == "__main__":
    print("Update Admin User")
    print("=" * 50)

    # Get user input
    username = input("Enter username (e.g., logadheenan): ").strip()
    email = input("Enter email (e.g., logadheenan@example.com): ").strip()
    display_name = input("Enter display name (e.g., Logadheenan): ").strip()
    password = input("Enter password: ").strip()

    if not all([username, email, display_name, password]):
        print("\n--- Error: All fields are required!")
        sys.exit(1)

    confirm = input(f"\nUpdate admin user to '{username}'? (yes/no): ")
    if confirm.lower() == 'yes':
        update_admin(username, email, display_name, password)
    else:
        print("Operation cancelled")
