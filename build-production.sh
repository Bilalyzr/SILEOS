#!/bin/bash

# Production Build Script
# Builds and deploys SashaInfinity LMS in a single container

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}🚀 SashaInfinity LMS Production Build${NC}"
echo "=========================================="

print_status() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check if Docker and Docker Compose are available
if ! command -v docker &> /dev/null; then
    print_error "Docker is not installed"
    exit 1
fi

if ! command -v docker-compose &> /dev/null; then
    print_error "Docker Compose is not installed"
    exit 1
fi

# Stop existing containers
print_status "Stopping existing containers..."
docker-compose -f docker-compose.production.yml down --remove-orphans

# Clean up old images
print_status "Cleaning up old images..."
docker system prune -f
docker image prune -f

# Build frontend first (separate stage)
print_status "Building frontend..."
cd frontend
if [ ! -f "package.json" ]; then
    print_error "Frontend package.json not found"
    exit 1
fi

npm install --legacy-peer-deps
npm run build --legacy-peer-deps
cd ..

# Copy frontend build to Docker context
print_status "Copying frontend build to Docker context..."
rm -rf frontend-build
mkdir -p frontend-build
cp -r frontend/dist frontend-build/

# Create production environment file if it doesn't exist
if [ ! -f ".env.production" ]; then
    print_status "Creating production environment file..."
    cat > .env.production << EOF
# Production Environment Variables
SECRET_KEY=your-secret-key-here
JWT_SECRET=your-jwt-secret-here
RAZORPAY_KEY=your-razorpay-key-here
RAZORPAY_SECRET=your-razorpay-secret-here
ADMIN_EMAIL=admin@sashainfinity.com
ADMIN_USERNAME=sashainfinity_admin
ADMIN_PASSWORD=CHANGE_ME_TO_A_STRONG_ADMIN_PASSWORD
FRONTEND_URL=https://lms.sashainfinity.com
BACKEND_URL=https://backend.sashainfinity.com
DOMAIN=sashainfinity.com
ENABLE_API_RATE_LIMITING=true
ENABLE_SECURITY_HEADERS=true
MIN_PASSWORD_LENGTH=12
SESSION_TIMEOUT_MINUTES=30
MAX_FILE_SIZE=10485760
SCAN_UPLOADED_FILES=true
CORS_ORIGINS=["https://lms.sashainfinity.com", "https://backend.sashainfinity.com"]
ALLOWED_HOSTS=["lms.sashainfinity.com", "backend.sashainfinity.com", "localhost"]
EOF
    print_warning "Please edit .env.production with your actual configuration"
fi

# Build the production image
print_status "Building production container..."
docker-compose -f docker-compose.production.yml build --no-cache

# Verify build
if [ $? -eq 0 ]; then
    print_status "Build completed successfully!"
else
    print_error "Build failed"
    exit 1
fi

print_status "Production build completed successfully!"
echo ""
echo "📋 Next steps:"
echo "1. Edit .env.production with your configuration"
echo "2. Run: docker-compose -f docker-compose.production.yml up -d"
echo "3. Check logs: docker-compose -f docker-compose.production.yml logs -f"
echo ""
echo "🔗 Access points after deployment:"
echo "  - Frontend: http://localhost"
echo "  - Health Check: http://localhost/health"
echo "  - Backend Docs: http://localhost/api/v1/docs"
echo ""