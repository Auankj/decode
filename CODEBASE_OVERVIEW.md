# Cookie-Licking Detector – Codebase Overview

## Project Structure

- **app/**: Main backend application package
  - **main.py**: FastAPI app entry point, includes all routers and middleware
  - **api/**: All API route modules (auth, claims, dashboard, repositories, users, webhooks, etc.)
  - **core/**: Core configuration, logging, monitoring, and security utilities
  - **db/**: Database connection and session management
  - **models/**: SQLAlchemy models for all database tables (claims, issues, repositories, etc.)
  - **services/**: Integrations and business logic (GitHub, notification, pattern matching, etc.)
  - **tasks/**: Celery background tasks (comment analysis, nudge checks, progress checks)
  - **utils/**: Utility modules (distributed locking, etc.)
  - **websockets/**: WebSocket manager and routes
  - **workers/**: Celery worker entry points and periodic/background jobs

## Main API Endpoints

All endpoints are prefixed with `/api/v1` unless otherwise noted.

### Authentication
- `POST /api/v1/auth/register` – Register a new user
- `POST /api/v1/auth/login` – Login and receive JWT tokens
- `POST /api/v1/auth/refresh` – Refresh access token
- `GET /api/v1/auth/me` – Get current user info
- `POST /api/v1/auth/logout` – Logout user
- `POST /api/v1/auth/api-keys` – Create API key
- `GET /api/v1/auth/api-keys` – List API keys
- `DELETE /api/v1/auth/api-keys/{key_id}` – Delete API key
- `POST /api/v1/auth/change-password` – Change password
- `POST /api/v1/auth/request-password-reset` – Request password reset
- `GET /api/v1/auth/admin/users` – List all users (admin only)

### Repositories
- `POST /api/v1/repositories` – Register a repository
- ... (other CRUD endpoints in repository_routes.py)

### Claims
- `GET /api/v1/claims` – List all claims
- ... (other claim management endpoints in claim_routes.py)

### Dashboard
- `GET /api/v1/dashboard/stats` – System statistics
- ... (other analytics endpoints in dashboard_routes.py)

### Webhooks
- `POST /api/v1/webhooks/github` – GitHub webhook integration

### Users
- ... (user management endpoints in user_routes.py)

### Settings
- ... (settings management endpoints in settings_routes.py)

### Websockets
- ... (real-time updates via websockets)

## Docs & Interactive API
- **Swagger UI**: `/docs`
- **OpenAPI Spec**: `/openapi.json`

---

For detailed request/response schemas, see the FastAPI docs at `/docs` when the backend is running.
