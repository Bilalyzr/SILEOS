#!/bin/bash

# SashaInfinity LMS Admin Creation Script
# This script creates/updates the admin user for the LMS

echo "🚀 SashaInfinity LMS Admin Creation Script"
echo "=========================================="

# Check if we're in the correct directory
if [ ! -f "docker-compose.yml" ]; then
    echo "❌ Error: docker-compose.yml not found. Please run this from the project root directory."
    exit 1
fi

# Check if Docker is running
if ! docker-compose ps > /dev/null 2>&1; then
    echo "❌ Error: Docker is not running. Please start Docker and try again."
    exit 1
fi

echo "📋 Current Admin Configuration:"
echo "   Email: ${ADMIN_EMAIL:-admin@sashainfinity.com}"
echo "   Username: ${ADMIN_USERNAME:-sashainfinity_admin}"
echo "   Password: [Set via ADMIN_PASSWORD environment variable]"
echo ""

# Confirm with user
read -p "Do you want to create/update the admin user? (y/N): " -n 1 -r
echo ""
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "❌ Admin creation cancelled."
    exit 0
fi

echo ""
echo "🔐 Creating admin user..."

# Run the admin seeding script
if docker-compose exec -T backend python seed_admin_simple.py; then
    echo ""
    echo "✅ Admin user created successfully!"
    echo ""
    echo "📋 Login Details:"
    echo "   URL: https://lms.sashainfinity.com/login"
    echo "   Email: ${ADMIN_EMAIL:-admin@sashainfinity.com}"
    echo "   Username: ${ADMIN_USERNAME:-sashainfinity_admin}"
    echo ""
    echo "⚠️  Remember to:"
    echo "   1. Change the default password after first login"
    echo "   2. Update the admin profile information"
    echo "   3. Configure system settings as needed"
else
    echo ""
    echo "❌ Error: Admin creation failed. Please check the logs above."
    echo "💡 You can check container logs with: docker-compose logs backend"
    exit 1
fi

echo ""
echo "🎉 Admin setup completed!"