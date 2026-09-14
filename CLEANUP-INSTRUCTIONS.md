# Delete All Courses - Instructions

## Option 1: Using SQL (Recommended - Fastest)

Run this command in your terminal:

```bash
cd /www/wwwroot/sasha_lms

docker-compose exec db psql -U sashainfinity -d sashainfinity_lms -c "
DELETE FROM quiz_answers;
DELETE FROM quiz_attempts;
DELETE FROM quiz_questions;
DELETE FROM quizzes;
DELETE FROM enrollments;
DELETE FROM payments;
DELETE FROM order_items;
DELETE FROM orders;
DELETE FROM lessons;
DELETE FROM course_categories;
DELETE FROM course_tags;
DELETE FROM courses;
"
```

## Option 2: Using the Batch File

Simply double-click: `delete-all-courses.bat`

## Option 3: Using Python Script

```bash
cd /www/wwwroot/sasha_lms

docker-compose exec backend python -m app.scripts.delete_all_courses
```

## Option 4: Direct SQL File

```bash
cd /www/wwwroot/sasha_lms

docker-compose exec -T db psql -U sashainfinity -d sashainfinity_lms < delete-courses.sql
```

## Option 5: Manual Database Access

1. Access the database container:
```bash
docker-compose exec db psql -U sashainfinity -d sashainfinity_lms
```

2. Run these commands one by one:
```sql
DELETE FROM quiz_answers;
DELETE FROM quiz_attempts;
DELETE FROM quiz_questions;
DELETE FROM quizzes;
DELETE FROM enrollments;
DELETE FROM payments;
DELETE FROM order_items;
DELETE FROM orders;
DELETE FROM lessons;
DELETE FROM course_categories;
DELETE FROM course_tags;
DELETE FROM courses;
```

3. Exit with `\q`

## Verify Deletion

Check if courses are deleted:
```bash
docker-compose exec db psql -U sashainfinity -d sashainfinity_lms -c "SELECT COUNT(*) FROM courses;"
```

## Reset Auto-Increment IDs (Optional)

If you want new courses to start from ID 1:
```bash
docker-compose exec db psql -U sashainfinity -d sashainfinity_lms -c "
ALTER SEQUENCE courses_id_seq RESTART WITH 1;
ALTER SEQUENCE lessons_id_seq RESTART WITH 1;
ALTER SEQUENCE enrollments_id_seq RESTART WITH 1;
"
```

## Clean Up Uploaded Files

To also delete uploaded images and videos:
```bash
docker-compose exec backend rm -rf /app/uploads/images/*
docker-compose exec backend rm -rf /app/uploads/videos/*
docker-compose exec backend rm -rf /app/uploads/documents/*
docker-compose exec backend rm -rf /app/uploads/temp/*
```

## After Cleanup

1. Refresh your browser
2. The instructor courses page should be empty
3. Create a new course from scratch
4. The new course should have proper ID sequencing

---

**Note**: This deletion is permanent and cannot be undone. Make sure you want to delete all courses before proceeding.
