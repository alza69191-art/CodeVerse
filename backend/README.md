# CodeVerse API

Initial FastAPI backend foundation.

## Included
- Registration, login, and current-user endpoint.
- Argon2 password hashing.
- JWT bearer authentication.
- User-owned repository metadata endpoints.
- SQLAlchemy models with SQLite for local development and PostgreSQL support through `DATABASE_URL`.
- Health endpoint at `/health`.

## Run locally

From the `backend` directory:

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
- `POST /api/v1/repositories` (Bearer token required)
- `GET /api/v1/repositories/mine` (Bearer token required)
- `GET /api/v1/repositories/{repository_id}` (owner only)
- `GET /health`

## Security status and production work
This is an initial backend foundation, not a production-ready Git hosting service.
- Never commit `.env`, JWT secrets, provider API keys, or encryption keys.
- Set a strong random `JWT_SECRET_KEY` and PostgreSQL `DATABASE_URL` in the deployment environment.
- Registration currently creates ordinary user accounts only. There is no public admin registration or role escalation endpoint.
- Repository records are metadata only; Git object storage, clone/push over Git smart HTTP, branch management, and access-control enforcement for Git transport are not implemented yet.
- Before production: add Alembic migrations, rate limiting, email verification, password reset, refresh-token rotation, CSRF protections where cookie auth is used, audit logs, backups, monitoring, and automated tests.
- Provider-secret storage and encryption are intentionally not exposed until a secure server-side key-management design is added.
