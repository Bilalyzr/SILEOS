# SashaInfinity LMS - Project Context & Instructions

Welcome to the **SashaInfinity LMS** project. This document serves as the primary instruction manual and context for AI agents working in this repository.

## 🎓 Project Overview

SashaInfinity LMS is a premium, full-stack Learning Management System designed for high performance, security, and a modern user experience. It supports course management, multi-role dashboards (Student, Instructor, Admin, Company), Razorpay payments, automated certificate generation, and specialized video streaming.

### Core Technology Stack

- **Frontend**: React 18 + TypeScript + Vite + TailwindCSS
  - **State Management**: Zustand
  - **Data Fetching**: React Query (TanStack Query)
  - **UI Primitives**: Radix UI + Lucide Icons + Framer Motion
- **Backend**: FastAPI (Python 3.10+) + SQLAlchemy + PostgreSQL 15 + Redis 7
  - **Auth**: JWT (Access & Refresh tokens) with Role-Based Access Control (RBAC)
  - **Validation**: Pydantic v2
  - **Background Tasks**: Celery (integrated but use carefully)
- **Streaming Service**: Standalone FastAPI service on port 8001 using `yt-dlp` for proxying YouTube videos without branding.
- **Mobile**: Flutter app (Riverpod for state management, Go Router for navigation).
- **Infrastructure**: Docker Compose, Nginx (Reverse Proxy), Let's Encrypt (SSL).

---

## 🏗️ Architecture & Services

The system is orchestrated via Docker Compose with the following primary services:

| Service | Host Port | Internal Port | Description |
| :--- | :--- | :--- | :--- |
| **Nginx** | `3100` (HTTP) | `80` | Primary entry point. Proxies to Frontend and Backend. |
| **Frontend** | None | `3000` | Vite dev server (reached via Nginx). |
| **Backend** | `8000` | `8000` | FastAPI application. |
| **Streaming** | `8001` | `8001` | Standalone video proxy service. |
| **Postgres** | `5432` | `5432` | Primary database (`tutor_lms`). |
| **Redis** | `6379` | `6379` | Caching, session management, and rate limiting. |

### Directory Structure

- `backend/app/`: FastAPI source code.
- `frontend/src/`: React source code.
- `flutter_app/`: Mobile application source.
- `streaming-service/`: Video proxy service source.
- `nginx/`: Nginx configuration.
- `scripts/`: Operational shell scripts (`setup.sh`, `create_admin.sh`, etc.).
- `uploads/`: Persistent volume for user-uploaded content (courses, avatars).
- `certificates/`: Persistent volume for generated and template certificates.

---

## 🚀 Development Workflows

### Setup & Running

1. **Initial Setup**: Run `chmod +x scripts/setup.sh && ./scripts/setup.sh`. This creates the `.env` file, builds containers, and prepares necessary directories.
2. **Start Services**: `docker-compose up -d`.
3. **Logs**: `docker-compose logs -f [service_name]`.
4. **Access**:
   - **App**: `http://localhost:3100`
   - **API Docs**: `http://localhost:8000/docs` (only if `ENVIRONMENT=development`)

### Backend Development

- **Entry Point**: `backend/app/main.py`.
- **Database Migrations**: There is no Alembic setup for automatic migrations in the usual sense. `init_db()` in `backend/app/core/database.py` creates tables on startup. Manual SQL migrations are found in `backend/migrations/`.
- **Models**: SQLAlchemy models are in `backend/app/models/`. Always update schemas in `backend/app/schemas/` when changing models.
- **Commands**:
  - Shell into backend: `docker-compose exec backend bash`
  - Run manually (outside Docker): `uvicorn app.main:app --reload`

### Frontend Development

- **Entry Point**: `frontend/src/main.tsx`.
- **API Calls**: Managed via a centralized Axios instance in `frontend/src/api/axios.ts`. Note the strict trailing slash logic in the request interceptor.
- **Zustand Stores**: Found in `frontend/src/store/`.
- **Commands**:
  - `npm run dev` (Vite dev server)
  - `npm run build` (Production build)
  - `npm run type-check` (Run `tsc`)

### Video Streaming Paths

The system uses three methods for video delivery:
1. **Direct YouTube Embed**: Standard iframe embedding.
2. **Server-Side Proxy**: `streaming-service` + `yt-dlp` to hide branding and support range requests.
3. **Bunny.net CDN**: Integration for high-performance direct video delivery.

---

## 🔐 Security & Conventions

- **Authentication**: JWT tokens are stored in the Auth store. Refresh tokens are supported.
- **Role-Based Access**: Roles include `Student`, `Instructor`, `Admin`, `Company`, and `CompanyManager`.
- **Trailing Slashes**: The backend (`main.py`) sets `redirect_slashes=False`. The frontend `axios.ts` interceptor contains a comprehensive list of which endpoints should or should not have trailing slashes. **Do not modify this list without confirming the FastAPI route definition.**
- **CORS**: Strict CORS is enforced. Allowed origins are defined in `.env` and `backend/app/core/cors.py`.
- **Input Validation**: Pydantic v2 is used for all request/response validation.

---

## 📝 Important Notes for AI Agents

1. **No Automated Tests**: Currently, there is a lack of automated test coverage. **Manual verification is mandatory** for all changes. Check `PLAN.md` for specific manual test steps for critical systems like payments and enrollment.
2. **Production vs. Development**: `/docs` and `/redoc` are disabled in production. Ensure `ENVIRONMENT=development` in your `.env` for local debugging.
3. **Company Portal**: This is a significant sub-system with specialized logic for internships, work logs, and attendance. Files related to this are mostly under `backend/app/routers/companies.py`, `internships.py`, and `company_dashboard.py`.
4. **Tamil Language Support**: The system has specific taxonomy and pages in Tamil (e.g., `category-meiporul.tsx`). These are intentional and part of the product's identity.
5. **Static Files**: `./uploads` and `./certificates` are bind-mounted into both the `backend` and `nginx` containers.

---

*Last Updated: June 8, 2026*
