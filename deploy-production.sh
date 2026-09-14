#!/bin/bash
# Production Deployment Script for SashaInfinity LMS
# Run this on your production server

set -e

echo "==================================="
echo "SashaInfinity LMS - Production Deploy"
echo "==================================="

# Navigate to project directory
cd /www/wwwroot/sasha_lms/sasha_lms/sasha_lms

echo ""
echo "1. Pulling latest code..."
git pull devesh main

echo ""
echo "2. Creating .env file if not exists..."
if [ ! -f .env ]; then
    cp .env.example .env
    echo "⚠️  Please update .env with your production values!"
fi

echo ""
echo "3. Stopping all services..."
docker-compose down

echo ""
echo "4. Building and starting services..."
docker-compose up -d --build

echo ""
echo "5. Waiting for services to be healthy..."
sleep 30

echo ""
echo "6. Checking service status..."
docker-compose ps

echo ""
echo "7. Running health checks..."
echo "Backend:"
curl -s http://localhost:8000/health || echo "❌ Backend health check failed"
echo ""
echo "Frontend:"
curl -s http://localhost:3000 > /dev/null && echo "✅ Frontend is responding"
echo ""
echo "Nginx:"
curl -s http://localhost:3100 > /dev/null && echo "✅ Nginx is responding"

echo ""
echo "==================================="
echo "Deployment completed!"
echo "==================================="
echo ""
echo "🌐 Access your site at:"
echo "   - Main: https://lms.sashainfinity.com"
echo "   - Backend: https://backend.sashainfinity.com"
echo ""
echo "📝 Don't forget to:"
echo "   1. Add 'lms.sashainfinity.com' to Firebase Authorized Domains"
echo "   2. Clear Cloudflare cache (if using)"
echo "   3. Update .env with production values (RAZORPAY, SMTP, etc.)"
echo ""
