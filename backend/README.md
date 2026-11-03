# CodeVerse API

FastAPI backend foundation with user accounts, repository metadata, local bare-Git storage, personal access tokens, and an initial Git smart-HTTP transport.

## Included
- Registration, login, and current-user endpoint.
- Argon2 password hashing and JWT bearer authentication.
- Personal access token creation, listing, and revocation. Raw tokens are shown only once; only SHA-256 hashes are stored.
- SQLAlchemy user, repository, and token models.
- Bare Git repository initialization.
- Git smart HTTP CGI bridge for clone/fetch/push, with private-repository and write-token checks.
- Owner-only repository metadata, branch-list, and commit-history endpoints.
- SQLite for local development and PostgreSQL support through `DATABASE_URL`.

## Run locally

Install Git (including `git-http-backend`) on the API host, then from the `backend` directory:

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
- `POST /api/v1/tokens` (create a personal access token)
- `GET /api/v1/tokens` (list token metadata)
- `DELETE /api/v1/tokens/{token_id}` (revoke token)
- `POST /api/v1/repositories` (creates a bare Git repository)
- `GET /api/v1/repositories/mine`
- `GET /api/v1/repositories/{repository_id}`
- `GET /api/v1/repositories/{repository_id}/branches`
- `GET /api/v1/repositories/{repository_id}/commits?limit=20`
- `GET|POST /git/{repository_id}.git/{git_path}` (Git smart HTTP)
- `GET /health`

## Git client setup
Create a personal access token in the account settings/API, enable read for clone/fetch, and enable write for push. Use the account username as the HTTP Basic username and the one-time token as its password. Do not put tokens in remote URLs or commit them to source files; let Git Credential Manager store credentials securely.

Example remote:
`https://YOUR-CODEVERSE-HOST/git/REPOSITORY_ID.git`

## Git storage
Bare repositories are stored under `REPOSITORY_STORAGE_PATH/<owner_id>/<repository_id>.git`. Use a persistent disk or volume for this directory in deployment. The filesystem path is generated from numeric database IDs, not user-controlled repository names.

## Security and production status
This is an early development foundation, not a production-ready Git hosting service.
- Serve Git endpoints over HTTPS only. Never commit `.env`, JWT secrets, provider API keys, or encryption keys.
- Set a strong random `JWT_SECRET_KEY`, PostgreSQL `DATABASE_URL`, and persistent `REPOSITORY_STORAGE_PATH` in deployment.
- Personal access tokens are stored as SHA-256 hashes and cannot be retrieved after creation. Revoke and replace a token if it is lost.
- Registration creates ordinary user accounts only; there is no public admin registration or role escalation endpoint.
- Git smart HTTP is an initial subprocess-based bridge. Before production, add strict request/response limits, concurrency controls, audit logs, hardened CGI environment, background handling for large pushes, comprehensive protocol tests, and security review.
- Existing database deployments need a migration for the new `personal_access_tokens` table; `create_all` only creates missing tables and does not replace a migration system.
- File browsing, branch creation API, pull requests, code review, collaboration, and scalable distributed Git storage are not implemented yet.
- Before production: add Alembic migrations, rate limiting, email verification, password reset, refresh-token rotation, CSRF protections where cookie auth is used, backups, monitoring, and automated tests.
- Provider-secret storage and encryption are intentionally not exposed until a secure server-side key-management design is added.
