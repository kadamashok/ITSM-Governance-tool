# ITSM Governance Tool

Enterprise ITSM governance platform with FastAPI backend, React dashboard, ServiceNow integration, SLA/governance analytics, and duplicate detection.

## Project Status

Current implementation includes:

- FastAPI backend on port `8050`
- React + Vite frontend on port `5178`
- ServiceNow integration using OAuth 2.0 (Azure AD Authorization Code flow)
- Encrypted in-memory storage for OAuth secrets/tokens (Fernet)
- Automatic access-token refresh using refresh token
- Executive, vendor, and engineer dashboards backed by live ServiceNow data
- Governance analytics and duplicate-detection APIs
- Period filters: `30m`, `1h`, `3h`, `8h`, `1d`, `5d`, `10d`, `15d`

## Tech Stack

### Backend

- Python 3.11
- FastAPI
- SQLAlchemy ORM
- Pydantic + pydantic-settings
- Requests
- Cryptography (Fernet)
- Scikit-learn
- Uvicorn
- PostgreSQL (primary) / SQLite (local fallback)

### Frontend

- React 18
- Vite
- TailwindCSS
- Axios
- Chart.js + react-chartjs-2

### DevOps

- Docker
- Docker Compose

## Architecture

- `app/api/` API router and endpoint modules
- `app/services/` business logic (OAuth, ServiceNow client, dashboards, sync, governance)
- `app/models/` SQLAlchemy entities
- `app/database/` session/engine setup
- `app/utils/` config, security, logging, review-period parsing
- `app/jobs/` scheduled sync jobs
- `frontend/` React SPA

## OAuth Flow (Azure AD)

1. Configure OAuth settings from frontend `/settings/servicenow`:
   - Instance URL
   - Client ID
   - Client Secret
   - Tenant ID
   - OAuth Scope
2. Frontend redirects to backend OAuth login route:
   - `GET /auth/login`
3. Backend redirects to Microsoft authorize endpoint.
4. Microsoft redirects back to:
   - `GET /auth/callback`
5. Backend exchanges auth code for access/refresh tokens and stores encrypted tokens in memory.
6. ServiceNow API calls use:
   - `Authorization: Bearer <access_token>`
7. Expired token is refreshed automatically.

## Local Setup

### 1. Backend

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --host 127.0.0.1 --port 8050 --reload
```

Backend URLs:

- API base: `http://127.0.0.1:8050`
- Docs: `http://127.0.0.1:8050/docs`
- Health: `http://127.0.0.1:8050/health`

### 2. Frontend

```bash
cd frontend
npm install
npm run dev -- --host 127.0.0.1 --port 5178
```

Frontend URL:

- `http://127.0.0.1:5178`

### 3. Docker (optional)

```bash
docker compose up --build
```

## Key Environment Variables

Defined in `.env` / `.env.example`:

- `APP_HOST`, `APP_PORT`, `APP_CORS_ORIGINS`
- `DATABASE_URL` (or PG connection vars)
- `SERVICENOW_ENCRYPTION_KEY`
- `SERVICENOW_OAUTH_REDIRECT_URI` (default `http://127.0.0.1:8050/auth/callback`)
- `FRONTEND_BASE_URL` (default `http://127.0.0.1:5178`)
- `SERVICENOW_TIMEOUT_SECONDS`, `SERVICENOW_PAGE_SIZE`

## API Endpoints

### System

- `GET /health`

### OAuth / Config

- `POST /config/servicenow`
- `GET /auth/login`
- `GET /auth/callback`
- `GET /config/status`

### Sync

- `GET /sync/incidents?period=1d`
- `POST /sync/run?period=1d`

### Analytics

- `GET /analytics/sla-summary?period=1d`
- `GET /analytics/governance-report?period=1d`
- `GET /analytics/duplicates`

### Dashboards

- `GET /dashboard/executive?period=1d&page=1&size=25`
- `GET /dashboard/vendor/{vendor_name}?period=1d`
- `GET /dashboard/engineer/{engineer_name}?period=1d`

## Notes

- Frontend uses Vite proxy for `/api/*` calls in development.
- OAuth login/callback routes (`/auth/*`) are called directly on backend host.
- If PostgreSQL is unavailable locally, use SQLite through `DATABASE_URL`.
