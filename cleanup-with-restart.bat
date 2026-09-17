@echo off
echo ========================================
echo  CLEANUP COURSES - WITH DB RESTART
echo ========================================
echo.

echo Step 1: Starting database container...
docker-compose up -d db
echo.
echo Waiting for database to be ready...
timeout /t 5 /nobreak > nul
echo.

echo Step 2: Deleting all courses and related data...
docker-compose exec db psql -U sashainfinity -d sashainfinity_lms -c "DELETE FROM quiz_answers; DELETE FROM quiz_attempts; DELETE FROM quiz_questions; DELETE FROM quizzes; DELETE FROM enrollments; DELETE FROM payments; DELETE FROM order_items; DELETE FROM orders; DELETE FROM lessons; DELETE FROM course_categories; DELETE FROM course_tags; DELETE FROM courses;"
echo.

echo Step 3: Resetting ID sequences...
docker-compose exec db psql -U sashainfinity -d sashainfinity_lms -c "ALTER SEQUENCE courses_id_seq RESTART WITH 1; ALTER SEQUENCE lessons_id_seq RESTART WITH 1; ALTER SEQUENCE enrollments_id_seq RESTART WITH 1;"
echo.

echo Step 4: Verifying deletion...
docker-compose exec db psql -U sashainfinity -d sashainfinity_lms -c "SELECT COUNT(*) as courses_count FROM courses;"
echo.

echo ========================================
echo  CLEANUP COMPLETE!
echo ========================================
echo.
echo All courses have been deleted.
echo Database is ready for new courses.
echo.
pause
