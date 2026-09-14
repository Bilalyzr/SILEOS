# SashaInfinity LMS Backend API

A complete FastAPI backend for the SashaInfinity LMS, providing premium learning management system functionality with modern technology stack.

## 🚀 Features

### Core Functionality
- **User Management**: Registration, authentication, profiles, and role-based access control
- **Course Management**: Complete CRUD operations, enrollment, progress tracking
- **Payment Processing**: Integrated with Razorpay for Indian market
- **Certificate Generation**: Automated certificate creation with PDF export
- **Admin Dashboard**: Comprehensive admin controls and analytics
- **Email Notifications**: Automated email system for user actions

### Technical Stack
- **FastAPI**: High-performance Python web framework
- **SQLAlchemy**: Modern Python SQL toolkit and ORM
- **PostgreSQL**: Robust relational database
- **Redis**: In-memory caching and session management
- **JWT**: Secure authentication with access/refresh tokens
- **Razorpay**: Payment gateway integration
- **Docker**: Containerized deployment

## 📋 Prerequisites

- Python 3.11+
- PostgreSQL 15+
- Redis 7+
- Docker & Docker Compose (for containerized setup)

## 🛠️ Installation

### Option 1: Docker Setup (Recommended)

1. Clone the repository and navigate to backend directory
```bash
cd sashainfinity-lms/backend
```

2. Copy environment file and configure
```bash
cp .env.example .env
# Edit .env with your configuration
```

3. Run with Docker Compose (from root directory)
```bash
docker-compose up --build
```

### Option 2: Local Development

1. Create virtual environment
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

2. Install dependencies
```bash
pip install -r requirements.txt
```

3. Configure environment
```bash
cp .env.example .env
# Edit .env with your database and service URLs
```

4. Run database migrations
```bash
alembic upgrade head
```

5. Start the server
```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

## 🔧 Configuration

### Environment Variables

Essential configuration variables in `.env`:

```env
# Database
DATABASE_URL=postgresql://user:password@localhost:5432/sashainfinity_lms

# Redis
REDIS_URL=redis://localhost:6379/0

# Security
SECRET_KEY=your-secret-key-min-32-characters
JWT_SECRET=your-jwt-secret

# Payment (Razorpay)
RAZORPAY_KEY_ID=your_key_id
RAZORPAY_KEY_SECRET=your_key_secret
RAZORPAY_WEBHOOK_SECRET=your_webhook_secret

# Email
SMTP_HOST=smtp.gmail.com
SMTP_USER=your-email@gmail.com
SMTP_PASSWORD=your-app-password
```

### Database Setup

The backend uses PostgreSQL with the following databases:
- Main application data
- User authentication and profiles
- Course content and enrollments
- Payment transactions
- Certificate records

## 📚 API Documentation

### Authentication Endpoints
- `POST /auth/login` - User login
- `POST /auth/register` - User registration
- `POST /auth/refresh` - Refresh access token
- `POST /auth/forgot-password` - Password reset request
- `GET /auth/me` - Get current user info

### Course Management
- `GET /courses/` - List courses with filters
- `GET /courses/{id}` - Get course details
- `POST /courses/` - Create course (instructor only)
- `PUT /courses/{id}` - Update course
- `POST /courses/{id}/enroll` - Enroll in course

### User Management
- `GET /users/profile` - Get user profile
- `PUT /users/profile` - Update profile
- `GET /users/stats` - Get user statistics
- `POST /users/apply-instructor` - Apply for instructor role

### Payment Processing
- `POST /payments/create-payment-intent` - Initialize payment
- `POST /payments/confirm-payment` - Confirm payment
- `GET /payments/transactions` - Get user transactions
- `POST /payments/webhook` - Payment webhook handler

### Certificate Management
- `GET /certificates/` - Get user certificates
- `POST /certificates/generate/{course_id}` - Generate certificate
- `GET /certificates/download/{id}` - Download certificate PDF
- `GET /certificates/verify/{code}` - Verify certificate

### Admin Operations
- `GET /admin/stats` - System statistics
- `GET /admin/users` - User management
- `GET /admin/courses` - Course management
- `GET /admin/revenue` - Revenue analytics

## 🔐 Security Features

- **JWT Authentication**: Secure token-based auth with refresh tokens
- **Password Hashing**: Bcrypt encryption for user passwords
- **Role-Based Access**: Student/Instructor/Admin permissions
- **Rate Limiting**: API endpoint protection
- **Input Validation**: Pydantic schema validation
- **CORS Protection**: Configurable cross-origin policies

## 💳 Payment Integration

Integrated with Razorpay for the Indian market:
- Secure payment processing
- Webhook verification
- Refund management
- Multi-payment methods (Cards, UPI, Net Banking, Wallets)
- Instructor earnings tracking

## 📧 Email System

Automated email notifications for:
- Account verification
- Password reset
- Course enrollment confirmation
- Certificate generation
- Payment confirmations

## 📊 Database Schema

The backend implements a comprehensive database structure for SashaInfinity LMS:

### Core Tables
- **users**: User accounts and authentication
- **user_profiles**: Extended user information
- **instructor_profiles**: Instructor-specific data
- **courses**: Course content and metadata
- **lessons**: Individual course lessons
- **quizzes**: Course assessments
- **enrollments**: Student course enrollments
- **payments**: Payment transactions
- **certificates**: Generated certificates

## 🚀 Deployment

### Docker Production Deployment

1. Configure production environment
```bash
cp .env.example .env.prod
# Set ENVIRONMENT=production
# Configure production database URLs
# Set secure SECRET_KEY and JWT_SECRET
```

2. Build and deploy
```bash
docker-compose -f docker-compose.prod.yml up -d
```

### Traditional Server Deployment

1. Install dependencies on server
2. Configure PostgreSQL and Redis
3. Set up reverse proxy (Nginx)
4. Configure SSL certificates
5. Set up process manager (systemd/supervisor)

## 🧪 Testing

Run the test suite:
```bash
pytest tests/
```

Run with coverage:
```bash
pytest --cov=app tests/
```

## 🔍 Monitoring

The backend includes:
- Health check endpoints (`/health`)
- Structured logging with configurable levels
- Optional Sentry integration for error tracking
- Performance metrics via Redis

## 📝 Development

### Code Quality
- **Black**: Code formatting
- **isort**: Import sorting
- **Flake8**: Linting
- **MyPy**: Type checking

Run quality checks:
```bash
black app/
isort app/
flake8 app/
mypy app/
```

### Database Migrations

Create new migration:
```bash
alembic revision --autogenerate -m "Description"
```

Apply migrations:
```bash
alembic upgrade head
```

## 🤝 Contributing

1. Fork the repository
2. Create feature branch
3. Make changes with tests
4. Run quality checks
5. Submit pull request

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 🔗 Related

- [Frontend Repository](../frontend/README.md)
- [Docker Setup](../docker-compose.yml)
- [Migration Plan](../SASHAINFINITY_LMS_MIGRATION_PLAN.md)