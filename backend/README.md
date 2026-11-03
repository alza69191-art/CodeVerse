# CodeVerse API

Initial FastAPI backend and local bare-Git storage foundation.

## Included
- Registration, login, and current-user endpoint.
- Argon2 password hashing and JWT bearer authentication.
- SQLAlchemy user and repository metadata models.
- Creation of real bare Git repositories on the API server.
- Owner-only repository metadata, branch-list, and commit-history endpoints.
- SQLite for local development and PostgreSQL support through `DATABASE_URL`.

## Run locally

Install Git on the API host, then from the `backend` directory:

```bash
python -m venv .venv
# Windows: .venv\\Scripts\\activate
# macOS/Linux: source .venv/bin/activate
pip install -r requirements.txt
# Copy .env.example to .env and set a strong JWT_SECRET_KEY.
uvicorn app.main:app --reload
```

API docs: `http://127.0.0.1:8000/docs`

## Endpoints
- `POST /api/v1/auth/register`
- `POST /api/v1/auth/login`
- `GET /api/v1/auth/me` (Bearer token required)
- `POST /api/v1/repositories` (creates a bare Git repository)
- `GET /api/v1/repositories/mine`
- `GET /api/v1/repositories/{repository_id}`
- `GET /api/v1/repositories/{repository_id}/branches`
- `GET /api/v1/repositories/{repository_id}/commits?limit=20`
- `GET /health`

## Git storage
Bare repositories are stored under `REPOSITORY_STORAGE_PATH/<owner_id>/<repository_id>.git`. Use a persistent disk or volume for this directory in deployment. The filesystem path is generated from numeric database IDs, not user-controlled repository names.

## Security and production status
This is an early development foundation, not a production-ready Git hosting service.
- Never commit `.env`, JWT secrets, provider API keys, or encryption keys.
- Set a strong random `JWT_SECRET_KEY`, PostgreSQL `DATABASE_URL`, and persistent `REPOSITORY_STORAGE_PATH` in deployment.
- Registration creates ordinary user accounts only; there is no public admin registration or role escalation endpoint.
- Repository records and bare Git storage are created, and owner-only branch/commit metadata can be read.
- Git smart HTTP transport (authenticated clone, fetch, push), file browsing, branch creation, pull requests, and collaboration are NOT implemented yet.
- Before production: add Alembic migrations, rate limiting, email verification, password reset, refresh-token rotation, CSRF protections where cookie auth is used, audit logs, backups, monitoring, and automated tests.
- Provider-secret storage and encryption are intentionally not exposed until a secure server-side key-management design is added.
