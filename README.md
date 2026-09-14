# 🎓 SashaInfinity LMS

**Premium Learning Management System built with React + Python + Docker**

SashaInfinity LMS is a modern, comprehensive learning management system designed for excellence in online education, built with cutting-edge technology for superior performance, security, and user experience.

The current Campus OS release adds school and college operations for admissions, tuition, daily action management, WhatsApp communications, custom domains, integrations, privacy, retention, and OneRoster export. See the [Campus OS release notes](docs/CAMPUS_OS_RELEASE_2026_09_11.md) for routes, migrations, and deployment steps.

## 🚀 Features

### ✅ **Comprehensive Learning Features**
- **Course Management**: Advanced course creation and management tools
- **User Dashboards**: Specialized interfaces for students/instructors/admins
- **Payment Integration**: Razorpay payment gateway for seamless transactions
- **Certificate System**: Professional template-based certificate generation
- **Progress Tracking**: Real-time lesson completion and quiz score monitoring
- **Video Streaming**: Secure, high-quality video lesson playback

### ✅ **Enhanced with Modern Tech**
- **React 18**: Fast, responsive frontend
- **FastAPI**: High-performance Python backend
- **PostgreSQL**: Robust database with full data migration
- **Redis**: Caching and session management
- **Docker**: Complete containerization for easy deployment

## 🏗️ Architecture

```
🌐 Nginx (Reverse Proxy + SSL)
├── ⚛️ React Frontend (Port 3000)
├── 🐍 FastAPI Backend (Port 8000)
├── 🗄️ PostgreSQL Database (Port 5432)
└── 🔴 Redis Cache (Port 6379)
```

## 🚀 Quick Start

### Prerequisites
- Docker & Docker Compose
- Git

### Installation

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd sashainfinity-lms
   ```

2. **Configure environment**
   ```bash
   cp .env.example .env
   # Edit .env with your configuration
   ```

3. **Start the application**
   ```bash
   chmod +x scripts/setup.sh
   ./scripts/setup.sh
   ```

4. **Access the application**
   - **Frontend**: http://localhost:3000
   - **Backend API**: http://localhost:8000
   - **API Documentation**: http://localhost:8000/docs

## 📚 Documentation

- [Migration Plan](TUTOR_LMS_MIGRATION_PLAN.md) - Complete migration strategy
- [API Documentation](docs/api.md) - Backend API reference
- [Component Guide](docs/components.md) - Frontend component library
- [Deployment Guide](docs/deployment.md) - Production deployment
- [Campus OS Release](docs/CAMPUS_OS_RELEASE_2026_09_11.md) - Schools and colleges feature set, routes, migrations, and rollout checklist

## 🛠️ Development

### Available Commands

```bash
# Start all services
docker-compose up -d

# View logs
docker-compose logs -f

# Stop services
docker-compose down

# Restart specific service
docker-compose restart backend

# Shell access
docker-compose exec backend bash
docker-compose exec frontend sh

# Database access
docker-compose exec postgres psql -U tutor -d tutor_lms
```

### Service URLs
- **Frontend Dev Server**: http://localhost:3000
- **Backend API**: http://localhost:8000
- **API Docs**: http://localhost:8000/docs
- **Database**: localhost:5432
- **Redis**: localhost:6379

## 📊 Migration from Legacy Systems

This system includes complete data migration from existing learning management systems:

- ✅ **All courses and lessons**
- ✅ **User accounts and profiles**
- ✅ **Enrollment data**
- ✅ **Progress tracking**
- ✅ **Payment history**
- ✅ **Certificates and templates**

See [Migration Plan](SASHAINFINITY_LMS_MIGRATION_PLAN.md) for detailed migration process.

## 🎨 UI/UX Replication

### SashaInfinity Theme
- **Colors**: Premium color palette for SashaInfinity brand
- **Typography**: Professional fonts (Poppins, etc.)
- **Layout**: Modern responsive design
- **Components**: Pixel-perfect UI components

### Page Templates
- 🏠 **Homepage**: Hero section, course grid, testimonials
- 📚 **Course Catalog**: Filter sidebar, course cards
- 📖 **Course Single**: Video player, curriculum sidebar
- 🎓 **Dashboard**: Navigation, stats, course management
- ➕ **Create Course**: Single-page form (no complex wizard)
- 📋 **My Courses**: Grid/list view, management tools

## 🔧 Technology Stack

### Frontend
- **React 18**: Modern component framework
- **Vite**: Fast build tool and dev server
- **TailwindCSS**: Utility-first styling
- **React Query**: Server state management
- **React Router**: Client-side routing
- **React Player**: Video playback
- **Chart.js**: Analytics visualization

### Backend
- **FastAPI**: High-performance Python framework
- **SQLAlchemy**: Database ORM
- **Alembic**: Database migrations
- **PostgreSQL**: Primary database
- **Redis**: Caching and sessions
- **Razorpay**: Payment processing
- **JWT**: Authentication tokens

### DevOps
- **Docker**: Containerization
- **Nginx**: Reverse proxy and load balancer
- **Let's Encrypt**: SSL certificates
- **GitHub Actions**: CI/CD pipeline

## 🔐 Security Features

- **JWT Authentication**: Secure token-based auth
- **Role-based Access**: Student/Instructor/Admin permissions
- **Input Validation**: All inputs sanitized and validated
- **File Upload Security**: Safe file handling
- **Payment Security**: Secure Razorpay integration
- **SSL/HTTPS**: Encrypted connections

## 📈 Performance

- **Fast Loading**: < 2s page load times
- **Caching**: Redis caching for better performance
- **Optimized Images**: Automatic image optimization
- **CDN Ready**: Static asset optimization
- **Database Optimization**: Indexed queries

## 🚀 Deployment

### Development
```bash
docker-compose up -d
```

### Production
```bash
docker-compose -f docker-compose.prod.yml up -d
```

### Environment Variables
See `.env.example` for all configuration options.

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Test thoroughly
5. Submit a pull request

## 📝 License

This project provides comprehensive learning management functionality for educational and development purposes.

## 🆘 Support

For support and questions:
- Check the [Documentation](docs/)
- Review the [Migration Plan](TUTOR_LMS_MIGRATION_PLAN.md)
- Open an issue for bugs or feature requests

---

**Built with ❤️ as a premium SashaInfinity LMS platform**# Sasha_lms
