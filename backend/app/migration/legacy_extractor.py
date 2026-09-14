#!/usr/bin/env python3
"""
Legacy LMS Data Extractor - Extract all data from legacy learning management systems
This script connects to your legacy MySQL database and extracts all data
"""
import mysql.connector
import json
import os
from datetime import datetime
from typing import Dict, List, Any
import argparse

class LegacyExtractor:
    def __init__(self, legacy_config: Dict[str, str]):
        """Initialize legacy extractor with database config"""
        self.legacy_config = legacy_config
        self.connection = None
        self.cursor = None
        self.extracted_data = {}

    def connect(self):
        """Connect to legacy MySQL database"""
        try:
            self.connection = mysql.connector.connect(
                host=self.legacy_config['DB_HOST'],
                user=self.legacy_config['DB_USER'],
                password=self.legacy_config['DB_PASSWORD'],
                database=self.legacy_config['DB_NAME'],
                charset='utf8mb4',
                port=self.legacy_config.get('DB_PORT', 3306)
            )
            self.cursor = self.connection.cursor(dictionary=True)
            print("✅ Connected to legacy database successfully!")
            return True
        except mysql.connector.Error as e:
            print(f"❌ Error connecting to legacy database: {e}")
            return False

    def extract_users(self):
        """Extract all users from legacy users table"""
        print("📋 Extracting users...")

        # Get users - adjust table name as needed for your legacy system
        try:
            self.cursor.execute("""
                SELECT * FROM users
                ORDER BY id
            """)
        except mysql.connector.Error:
            # Try common legacy table names (whitelist to prevent SQL injection)
            allowed_tables = ['wp_users', 'lms_users', 'users_legacy']
            for table_name in allowed_tables:
                try:
                    # Validate table name is alphanumeric + underscore only
                    if not table_name.replace('_', '').isalnum():
                        continue
                    query = f"SELECT * FROM {table_name} ORDER BY id"
                    self.cursor.execute(query)
                    break
                except mysql.connector.Error:
                    continue
            else:
                print("   ⚠️ No users table found")
                return

        users = self.cursor.fetchall()

        # Get user meta for each user if exists
        for user in users:
            user_id = user.get('ID') or user.get('id')
            if user_id:
                try:
                    self.cursor.execute("""
                        SELECT meta_key, meta_value
                        FROM usermeta
                        WHERE user_id = %s
                    """, (user_id,))
                    meta_data = {}
                    for meta in self.cursor.fetchall():
                        meta_data[meta['meta_key']] = meta['meta_value']
                    user['meta_data'] = meta_data
                except mysql.connector.Error:
                    user['meta_data'] = {}

        self.extracted_data['users'] = users
        print(f"   ✓ Extracted {len(users)} users with metadata")

    def extract_courses(self):
        """Extract all courses from legacy courses table"""
        print("📋 Extracting courses...")

        # Try different course table patterns
        course_queries = [
            "SELECT * FROM courses ORDER BY id",
            "SELECT * FROM posts WHERE post_type = 'courses' ORDER BY id",
            "SELECT * FROM course_data ORDER BY course_id"
        ]

        courses = []
        for query in course_queries:
            try:
                self.cursor.execute(query)
                courses = self.cursor.fetchall()
                break
            except mysql.connector.Error:
                continue

        if not courses:
            print("   ⚠️ No courses found")
            return

        # Get course meta for each course
        for course in courses:
            course_id = course.get('ID') or course.get('id') or course.get('course_id')
            if course_id:
                try:
                    self.cursor.execute("""
                        SELECT meta_key, meta_value
                        FROM postmeta
                        WHERE post_id = %s
                    """, (course_id,))
                    meta_data = {}
                    for meta in self.cursor.fetchall():
                        meta_data[meta['meta_key']] = meta['meta_value']
                    course['meta_data'] = meta_data
                except mysql.connector.Error:
                    course['meta_data'] = {}

        self.extracted_data['courses'] = courses
        print(f"   ✓ Extracted {len(courses)} courses with metadata")

    def extract_all_data(self):
        """Extract all data from legacy LMS"""
        if not self.connect():
            return False

        print("🚀 Starting legacy data extraction...")
        print(f"📊 Extracting from database: {self.legacy_config['DB_NAME']}")

        try:
            self.extract_users()
            self.extract_courses()

            # Add extraction metadata
            self.extracted_data['extraction_metadata'] = {
                'extraction_date': datetime.now().isoformat(),
                'legacy_system': 'unknown',
                'database_name': self.legacy_config['DB_NAME'],
                'extractor_version': '1.0.0'
            }

            print("✅ All data extracted successfully!")
            return True

        except Exception as e:
            print(f"❌ Error during extraction: {e}")
            return False
        finally:
            if self.cursor:
                self.cursor.close()
            if self.connection:
                self.connection.close()

    def save_to_json(self, output_file: str = "legacy_data.json"):
        """Save extracted data to JSON file"""
        try:
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(self.extracted_data, f, indent=2, ensure_ascii=False, default=str)

            file_size = os.path.getsize(output_file) / (1024 * 1024)  # MB
            print(f"💾 Data saved to {output_file} ({file_size:.2f} MB)")
            return True
        except Exception as e:
            print(f"❌ Error saving data: {e}")
            return False

def load_legacy_config(site_path: str) -> Dict[str, str]:
    """Load legacy system configuration from config file"""
    config_paths = [
        os.path.join(site_path, 'wp-config.php'),
        os.path.join(site_path, 'config.php'),
        os.path.join(site_path, 'database.php')
    ]

    config = {}

    for config_path in config_paths:
        if not os.path.exists(config_path):
            continue

        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                content = f.read()

            # Extract database configuration
            import re

            patterns = {
                'DB_NAME': r"define\s*\(\s*['\"]DB_NAME['\"]\s*,\s*['\"]([^'\"]+)['\"]",
                'DB_USER': r"define\s*\(\s*['\"]DB_USER['\"]\s*,\s*['\"]([^'\"]+)['\"]",
                'DB_PASSWORD': r"define\s*\(\s*['\"]DB_PASSWORD['\"]\s*,\s*['\"]([^'\"]*)['\"]",
                'DB_HOST': r"define\s*\(\s*['\"]DB_HOST['\"]\s*,\s*['\"]([^'\"]+)['\"]",
            }

            for key, pattern in patterns.items():
                match = re.search(pattern, content)
                if match:
                    config[key] = match.group(1)

            if config:
                break

        except Exception as e:
            print(f"⚠️ Error reading {config_path}: {e}")
            continue

    if not config:
        print("❌ No legacy configuration found. Please provide database details manually.")
        print("Example: python legacy_extractor.py --host localhost --db_name mydb --db_user user --db_pass pass")
        return {}

    # Set defaults
    if 'DB_HOST' not in config:
        config['DB_HOST'] = 'localhost'

    # Extract port if specified in host
    if ':' in config.get('DB_HOST', ''):
        host_parts = config['DB_HOST'].split(':')
        config['DB_HOST'] = host_parts[0]
        config['DB_PORT'] = int(host_parts[1])
    else:
        config['DB_PORT'] = 3306

    print("✅ Legacy configuration loaded successfully!")
    print(f"   Database: {config.get('DB_NAME', 'unknown')}")
    print(f"   Host: {config.get('DB_HOST', 'unknown')}:{config.get('DB_PORT', 3306)}")
    print(f"   User: {config.get('DB_USER', 'unknown')}")

    return config

def main():
    parser = argparse.ArgumentParser(description='Extract data from legacy LMS system')
    parser.add_argument('legacy_path', nargs='?', help='Path to legacy system installation directory')
    parser.add_argument('-o', '--output', default='legacy_data.json', help='Output JSON file')
    parser.add_argument('--host', help='Database host (override config)')
    parser.add_argument('--db_name', help='Database name (override config)')
    parser.add_argument('--db_user', help='Database user (override config)')
    parser.add_argument('--db_pass', help='Database password (override config)')
    parser.add_argument('--port', type=int, default=3306, help='Database port (override config)')

    args = parser.parse_args()

    # Load configuration
    if args.legacy_path:
        legacy_config = load_legacy_config(args.legacy_path)
        if not legacy_config:
            print("❌ Failed to load legacy configuration")
            return
    else:
        # Use command line arguments
        if not all([args.host, args.db_name, args.db_user]):
            print("❌ Please provide legacy_path or database connection details")
            return
        legacy_config = {
            'DB_HOST': args.host,
            'DB_NAME': args.db_name,
            'DB_USER': args.db_user,
            'DB_PASSWORD': args.db_pass or '',
            'DB_PORT': args.port
        }

    # Extract data
    extractor = LegacyExtractor(legacy_config)
    if extractor.extract_all_data():
        if extractor.save_to_json(args.output):
            print(f"🎉 Legacy data extraction completed successfully!")
            print(f"   Output file: {args.output}")
            print("   Next step: Run the PostgreSQL migration script")
        else:
            print("❌ Failed to save extracted data")
    else:
        print("❌ Data extraction failed")

if __name__ == "__main__":
    main()