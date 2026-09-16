@echo off
echo Restarting Backend Server...
echo.

cd /d "%~dp0"

echo Stopping backend container...
docker-compose stop backend

echo.
echo Starting backend container...
docker-compose up -d backend

echo.
echo Waiting for backend to start...
timeout /t 5 /nobreak > nul

echo.
echo Checking backend status...
docker-compose ps backend

echo.
echo Checking backend logs...
docker-compose logs --tail=50 backend

echo.
echo Backend restart complete!
echo.
pause
