from sqlalchemy import text
from app.core.database import engine

with engine.connect() as conn:
    result = conn.execute(text('SELECT id, post_title, post_parent FROM lessons LIMIT 10'))
    print('=== LESSONS IN DATABASE ===')
    for row in result:
        print(f'ID: {row[0]}, Title: {row[1]}, post_parent: {row[2]}')

    result2 = conn.execute(text('SELECT id, post_title FROM courses LIMIT 5'))
    print('\n=== COURSES IN DATABASE ===')
    for row in result2:
        print(f'ID: {row[0]}, Title: {row[1]}')
