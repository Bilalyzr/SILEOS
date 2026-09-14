#!/bin/bash

# YouTube Streaming Service Deployment Script
# This script rebuilds and deploys the complete Docker setup with new streaming service

set -e

echo "🚀 Starting YouTube Streaming Service Deployment"
echo "=================================================="

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Stop existing containers
print_status "Stopping existing containers..."
docker-compose down || true

# Clean up old images
print_status "Cleaning up old images..."
docker system prune -f

# Build streaming service
print_status "Building streaming service..."
cd streaming-service
docker build -t sashainfinity-streaming-service .
cd ..

# Build frontend
print_status "Building frontend..."
cd frontend
docker build -t sashainfinity-frontend .
cd ..

# Build backend
print_status "Building backend..."
cd backend
docker build -t sashainfinity-backend .
cd ..

# Start all services
print_status "Starting all services..."
docker-compose up -d

# Wait for services to be ready
print_status "Waiting for services to be ready..."
sleep 30

# Check service status
print_status "Checking service status..."
docker-compose ps

# Test streaming service
print_status "Testing streaming service health..."
curl -f http://localhost:8001/health || print_error "Streaming service health check failed"

print_status "Testing streaming service root endpoint..."
curl -f http://localhost:8001/ || print_error "Streaming service root check failed"

# Test backend health
print_status "Testing backend health..."
curl -f http://localhost:8000/health || print_error "Backend health check failed"

# Test frontend
print_status "Testing frontend..."
curl -f http://localhost:3100 || print_error "Frontend health check failed"

print_status "✅ Deployment completed successfully!"
echo ""
echo "📊 Service Status:"
docker-compose ps
echo ""
echo "🔗 Access Points:"
echo "  - Frontend: http://localhost:3100"
echo "  - Backend API: http://localhost:8000/api/v1"
echo "  - Streaming Service: http://localhost:8001"
echo "  - Backend Docs: http://localhost:8000/docs"
echo ""
echo "🎯 New Streaming Endpoints:"
echo "  - Stream Video: http://localhost:8000/api/v1/stream/{video_id}"
echo "  - Video Info: http://localhost:8000/api/v1/stream/info/{video_id}"
echo "  - Extract: http://localhost:8000/api/v1/stream/extract"
echo ""
echo "🔧 Old method is commented out and available for reference in:"
echo "  - /backend/app/routers/video.py"
echo ""
echo "📁 Service Locations:"
echo "  - Streaming Service: /streaming-service/"
echo "  - Frontend: /frontend/"
echo "  - Backend: /backend/"