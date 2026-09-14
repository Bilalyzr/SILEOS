#!/bin/bash

# SashaInfinity LMS - Development Setup Script
echo "🚀 Setting up SashaInfinity LMS Development Environment..."

# Check if Docker is installed
if ! command -v docker &> /dev/null; then
    echo "❌ Docker is not installed. Please install Docker and try again."
    exit 1
fi

# Check if Docker Compose is installed
if ! command -v docker-compose &> /dev/null; then
    echo "❌ Docker Compose is not installed. Please install Docker Compose and try again."
    exit 1
fi

# Create .env file if it doesn't exist
if [ ! -f .env ]; then
    echo "📝 Creating .env file from template..."
    cp .env.example .env
    echo "⚠️  Please edit .env file with your configuration before continuing."
    read -p "Press Enter after you've configured the .env file..."
fi

# Create necessary directories
echo "📁 Creating required directories..."
mkdir -p uploads/{courses,profiles,certificates,temp}
mkdir -p certificates/{templates,generated}
mkdir -p logs
mkdir -p database/backups

# Set permissions
echo "🔐 Setting file permissions..."
chmod +x scripts/*.sh
chmod 755 uploads certificates logs database/backups

# Build and start services
echo "🐳 Building Docker containers..."
docker-compose build

echo "🚀 Starting services..."
docker-compose up -d

# Wait for services to be ready
echo "⏳ Waiting for services to start..."
sleep 30

# Check service health
echo "🔍 Checking service health..."
if curl -f http://localhost:8000/health > /dev/null 2>&1; then
    echo "✅ Backend is healthy"
else
    echo "❌ Backend health check failed"
fi

if curl -f http://localhost:3000 > /dev/null 2>&1; then
    echo "✅ Frontend is accessible"
else
    echo "❌ Frontend is not accessible"
fi

# Show running services
echo "📊 Service Status:"
docker-compose ps

echo ""
echo "🎉 Setup Complete!"
echo ""
echo "📱 Frontend: http://localhost:3000"
echo "🔧 Backend API: http://localhost:8000"
echo "📚 API Docs: http://localhost:8000/docs"
echo "🗄️ Database: localhost:5432"
echo "🔴 Redis: localhost:6379"
echo ""
echo "🛠️  Useful Commands:"
echo "  View logs: docker-compose logs -f"
echo "  Stop services: docker-compose down"
echo "  Restart services: docker-compose restart"
echo "  Shell into backend: docker-compose exec backend bash"
echo "  Shell into frontend: docker-compose exec frontend sh"
echo ""