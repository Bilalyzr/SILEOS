@echo off
echo ========================================
echo  DELETE ALL COURSES - CLEANUP SCRIPT
echo ========================================
echo.
echo WARNING: This will delete ALL courses and related data!
echo.
pause

echo.
echo Connecting to database and running cleanup...
echo.

docker-compose exec db psql -U sashainfinity -d sashainfinity_lms -f /docker-entrypoint-initdb.d/delete-courses.sql

echo.
echo ========================================
echo  CLEANUP COMPLETE!
echo ========================================
echo.
echo All courses, lessons, enrollments, and related data have been deleted.
echo You can now create new courses from scratch.
echo.
pause
