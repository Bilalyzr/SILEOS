#!/usr/bin/env python3
"""
Migrate WooCommerce orders from WordPress to FastAPI database.
Reads WordPress backup SQL and creates orders/order_items in LMS database.
"""
import os
import re
import sys
from datetime import datetime
from decimal import Decimal

# Add parent directory to path for imports
sys.path.insert(0, '/app')

from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker


def parse_wp_orders(sql_file_path):
    """Parse WooCommerce orders from WordPress SQL backup."""
    orders = {}

    # Parse wc_orders
    with open(sql_file_path, 'r', encoding='utf-8', errors='ignore') as f:
        content = f.read()

    # Extract wc_orders INSERT statements
    wc_orders_pattern = r"INSERT INTO `wp_3b4ee1_wc_orders` VALUES \((.+?)\);"
    for match in re.finditer(wc_orders_pattern, content, re.DOTALL):
        values_str = match.group(1)
        # Parse individual order tuples
        order_pattern = r"\((\d+),'([^']+)','([^']+)','[^']+',[\d.]+,[\d.]+,\d+,'([^']+)'"
        for order_match in re.finditer(order_pattern, values_str):
            order_id = int(order_match.group(1))
            status = order_match.group(2)
            currency = order_match.group(3)
            email = order_match.group(4)
            orders[order_id] = {
                'id': order_id,
                'status': status,
                'currency': currency,
                'email': email,
                'items': []
            }

    # Extract woocommerce_order_items
    items_pattern = r"INSERT INTO `wp_3b4ee1_woocommerce_order_items` VALUES \((.+?)\);"
    for match in re.finditer(items_pattern, content, re.DOTALL):
        values_str = match.group(1)
        # Parse item tuples: (item_id, name, type, order_id)
        item_pattern = r"\((\d+),'([^']+)','([^']+)',(\d+)\)"
        for item_match in re.finditer(item_pattern, values_str):
            item_id = int(item_match.group(1))
            name = item_match.group(2)
            item_type = item_match.group(3)
            order_id = int(item_match.group(4))

            if order_id in orders and item_type == 'line_item':
                orders[order_id]['items'].append(name)

    # Filter to only completed/processing orders with items
    valid_orders = {}
    for order_id, order_data in orders.items():
        if order_data['items'] and order_data['status'] in ['wc-completed', 'wc-processing', 'wc-pending']:
            valid_orders[order_id] = order_data

    return valid_orders


def migrate_orders(db_session, wp_orders):
    """Migrate parsed WordPress orders to FastAPI database."""
    # Get course name to ID mapping
    course_result = db_session.execute(text("SELECT id, post_title FROM courses"))
    course_map = {row[1].lower().strip(): row[0] for row in course_result}

    # Get user email to ID mapping
    user_result = db_session.execute(text("SELECT id, user_email FROM users"))
    user_map = {row[1]: row[0] for row in user_result}

    migrated_count = 0
    skipped_count = 0

    for order_id, wp_order in wp_orders.items():
        email = wp_order['email']

        # Skip if user not found
        if email not in user_map:
            print(f"Skipping order {order_id}: User {email} not found")
            skipped_count += 1
            continue

        user_id = user_map[email]

        # Find matching courses
        course_ids = []
        for item_name in wp_order['items']:
            item_lower = item_name.lower().strip()
            # Try exact match first
            if item_lower in course_map:
                course_ids.append(course_map[item_lower])
            else:
                # Try partial match
                for course_name, course_id in course_map.items():
                    if item_lower in course_name or course_name in item_lower:
                        course_ids.append(course_id)
                        break

        if not course_ids:
            print(f"Skipping order {order_id}: No matching courses found for items: {wp_order['items']}")
            skipped_count += 1
            continue

        # Calculate total amount (use default prices from courses table)
        total_amount = Decimal('0')
        for course_id in course_ids:
            price_result = db_session.execute(
                text(f"SELECT course_price FROM courses WHERE id = {course_id}")
            )
            row = price_result.first()
            if row and row[0]:
                total_amount += Decimal(str(row[0]))

        # Create order
        order_key = f"WP-MIG-{order_id}"
        status_map = {
            'wc-completed': 'COMPLETED',
            'wc-processing': 'COMPLETED',
            'wc-pending': 'PENDING'
        }
        order_status = status_map.get(wp_order['status'], 'PENDING')

        # Insert order
        order_insert = text("""
            INSERT INTO orders (user_id, order_key, order_status, currency, total_amount,
                               subtotal_amount, payment_method, created_at, updated_at)
            VALUES (:user_id, :order_key, :order_status, :currency, :total_amount,
                    :subtotal_amount, :payment_method, :created_at, :updated_at)
            RETURNING id
        """)

        order_result = db_session.execute(order_insert, {
            'user_id': user_id,
            'order_key': order_key,
            'order_status': order_status,
            'currency': 'INR',
            'total_amount': total_amount,
            'subtotal_amount': total_amount,
            'payment_method': 'razorpay',
            'created_at': datetime.now(),
            'updated_at': datetime.now()
        })

        new_order_id = order_result.first()[0]

        # Create order items
        for course_id in course_ids:
            # Get course details
            course_result = db_session.execute(
                text(f"SELECT post_title, course_price FROM courses WHERE id = {course_id}")
            )
            course_row = course_result.first()
            if course_row:
                course_title, course_price = course_row

                order_item_insert = text("""
                    INSERT INTO order_items (order_id, course_id, order_item_name,
                                            order_item_type, quantity, subtotal, total)
                    VALUES (:order_id, :course_id, :order_item_name, :order_item_type,
                            :quantity, :subtotal, :total)
                """)

                db_session.execute(order_item_insert, {
                    'order_id': new_order_id,
                    'course_id': course_id,
                    'order_item_name': course_title,
                    'order_item_type': 'course',
                    'quantity': 1,
                    'subtotal': Decimal(str(course_price)) if course_price else Decimal('0'),
                    'total': Decimal(str(course_price)) if course_price else Decimal('0')
                })

        # Update enrollments with order_id
        for course_id in course_ids:
            enrollment_update = text("""
                UPDATE enrollments
                SET order_id = :order_id
                WHERE user_id = :user_id AND course_id = :course_id AND order_id IS NULL
            """)
            db_session.execute(enrollment_update, {
                'order_id': new_order_id,
                'user_id': user_id,
                'course_id': course_id
            })

        migrated_count += 1
        print(f"Migrated order {order_id} -> FastAPI order {new_order_id} for {email}")

    db_session.commit()
    return migrated_count, skipped_count


def main():
    sql_file_path = '/tmp/wordpress_backup.sql'

    print("Parsing WordPress orders...")
    wp_orders = parse_wp_orders(sql_file_path)
    print(f"Found {len(wp_orders)} valid WordPress orders")

    # Connect to database (never hardcode credentials — read from environment)
    db_url = os.environ.get("DATABASE_URL")
    if not db_url:
        raise SystemExit("DATABASE_URL environment variable is required")
    engine = create_engine(db_url)
    Session = sessionmaker(bind=engine)
    session = Session()

    try:
        print("\nMigrating orders to FastAPI database...")
        migrated, skipped = migrate_orders(session, wp_orders)
        print(f"\nMigration complete:")
        print(f"  - Migrated: {migrated} orders")
        print(f"  - Skipped: {skipped} orders")

    except Exception as e:
        print(f"Error during migration: {e}")
        session.rollback()
        raise
    finally:
        session.close()


if __name__ == '__main__':
    main()
