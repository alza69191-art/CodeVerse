# CodeVerse API

FastAPI backend with user accounts, bare Git storage, personal access tokens, Git smart HTTP, and a browser code workspace.

## Included
- Registration, login, current-user endpoint, Argon2 password hashing, and JWT authentication.
- Personal access tokens stored as SHA-256 hashes.
- Bare Git repositories, branch management, commit history, file listing, UTF-8 preview, authenticated text edits, and binary-safe file uploads.
- SQLite for development and PostgreSQL through `DATABASE_URL`.

## Run locally
Install Git on the API host, then from `backend`:

```bash
python -m venv .venv
# Windows: .venv\Scripts\activate
# macOS/Linux: source .venv/bin/activate
pip install -r requirements.txt
# Copy .env.example to .env and set a strong JWT_SECRET_KEY.
uvicorn app.main:app --reload
```

API docs: `http://127.0.0.1:8000/docs`. Open `workspace.html` and set the API URL. Configure `CORS_ORIGINS` to include the exact frontend origin.

## Endpoints
- `POST /api/v1/auth/register`, `POST /api/v1/auth/login`, `GET /api/v1/auth/me`
- `POST /api/v1/tokens`, `GET /api/v1/tokens`, `DELETE /api/v1/tokens/{token_id}`
- `POST /api/v1/repositories`, `GET /api/v1/repositories/mine`
- `GET /api/v1/repositories/{id}/branches`, `POST /api/v1/repositories/{id}/branches`
- `GET /api/v1/repositories/{id}/files`, `GET /api/v1/repositories/{id}/file`
- `PUT /api/v1/repositories/{id}/file` with JSON `path`, `content`, `branch`, `message`; creates a Git commit. Text limit: 1 MB.\n- `POST /api/v1/repositories/{id}/upload` with JSON `path`, `content_base64`, `branch`, `message`; stores binary or text file bytes in a Git commit. Upload limit: 10 MB per file.
- `GET /api/v1/repositories/{id}/commits`, Git smart HTTP, and `GET /health`.

## File-save behavior
The API checks repository ownership, validates relative paths, limits UTF-8 text files to 1 MB, writes blob/tree objects using Git plumbing, creates a commit, then updates the branch with compare-and-swap using Git update-ref. Concurrent updates are rejected; refresh and retry. Files are saved as regular files (mode 100644). File uploads support binary bytes via base64; each upload creates its own commit. File deletion and batch-atomic folder commits are not implemented.

## Security and production status
This is an early development foundation, not production-ready. Use HTTPS, persistent Git storage, strong JWT secrets, database migrations, rate limits, audit logs, request limits, backups, monitoring, automated protocol tests, and a security review before production. Never commit `.env` or provider API keys. Provider-secret storage is not implemented.
