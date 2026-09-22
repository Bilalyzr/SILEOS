#!/bin/bash

# Production Container Entrypoint Script
# Initializes and runs all services in a single container

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}🚀 Starting SashaInfinity LMS Production Container${NC}"
echo "=================================================="

# Function to print status
print_status() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

# Function to print warning
print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

# Function to print error
print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Initialize directories
print_status "Initializing directories..."
mkdir -p /var/log/supervisor
mkdir -p /app/uploads
mkdir -p /app/certificates
mkdir -p /app/streaming/cache
mkdir -p /var/cache/nginx
mkdir -p /var/log/nginx

# Set proper permissions
print_status "Setting permissions..."
chown -R root:root /app
chmod -R 755 /app
chmod -R 777 /app/uploads
chmod -R 777 /app/certificates

# Check if required files exist
if [ ! -f "/app/backend/app/main.py" ]; then
    print_error "Backend application not found"
    exit 1
fi

if [ ! -f "/app/streaming/video_streaming.py" ]; then
    print_error "Streaming service not found"
    exit 1
fi

# Wait for any dependencies (if needed)
print_status "Checking dependencies..."

# Initialize Python environment
cd /app/backend
print_status "Installing Python dependencies..."
pip install --no-cache-dir -r requirements.txt || print_warning "Backend dependencies install failed"

cd /app/streaming
print_status "Installing streaming dependencies..."
pip install --no-cache-dir -r requirements.txt || print_warning "Streaming dependencies install failed"

# Go back to app root
cd /app

# Initialize database (if needed)
print_status "Initializing database..."
python -c "import asyncio; from app.core.database import init_db; asyncio.run(init_db())" || print_warning "Database initialization failed"

# Initialize Redis (if needed)
print_status "Initializing Redis..."
python -c "import asyncio; from app.core.redis import init_redis; asyncio.run(init_redis())" || print_warning "Redis initialization failed"

# Create upload directories
print_status "Creating upload directories..."
mkdir -p /app/uploads/videos
mkdir -p /app/uploads/images
mkdir -p /app/certificates/generated

# Start Supervisor
print_status "Starting Supervisor..."
exec supervisord -c /etc/supervisor/conf.d/supervisord.conf