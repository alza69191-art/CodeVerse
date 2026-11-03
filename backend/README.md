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


## Collaboration: Issues and Pull Requests

All collaboration routes currently require an authenticated repository owner. This first version is owner-only; team membership and collaborator permissions are not implemented.

- `GET /api/v1/repositories/{id}/issues`
- `POST /api/v1/repositories/{id}/issues` with `title` and optional `body`
- `GET /api/v1/repositories/{id}/issues/{issue_id}` returns issue and comments
- `POST /api/v1/repositories/{id}/issues/{issue_id}/comments` with `body`
- `POST /api/v1/repositories/{id}/issues/{issue_id}/close`
- `GET /api/v1/repositories/{id}/pull-requests`
- `POST /api/v1/repositories/{id}/pull-requests` with `title`, `body`, `head_branch`, and `base_branch`
- `POST /api/v1/repositories/{id}/pull-requests/{pull_request_id}/close`

Pull Requests validate that both branches exist and are different. They are tracking records only: diff review, approvals, merge execution, conflict resolution, and branch protection are not implemented. New SQLAlchemy tables are created at application startup for fresh or existing databases; use Alembic migrations for production schema evolution.


## Repository teams and invitations

Repository owners can invite existing CodeVerse accounts by username. Invitees see pending invitations in their workspace and can accept or decline.

- `GET /api/v1/repositories/{id}/members` (owner)
- `POST /api/v1/repositories/{id}/members/invite` with `username` and `role` (`read` or `write`)
- `PUT /api/v1/repositories/{id}/members/{member_id}/role` (owner)
- `DELETE /api/v1/repositories/{id}/members/{member_id}` (owner)
- `GET /api/v1/users/me/invitations`
- `POST /api/v1/invitations/{invitation_id}/accept`
- `POST /api/v1/invitations/{invitation_id}/decline`

Active `read` members can inspect repository files, branches, commits, issues, and pull requests. Active `write` members can also create branches, save/upload files, create and comment on issues, close issues, and open/close pull requests. Only the owner can invite, change roles, or remove members. Invitations are for existing registered usernames; email delivery is not configured.


## Pull request review and merge

- `GET /api/v1/repositories/{id}/pull-requests/{pull_request_id}/diff` returns a branch diff and stat summary. The text patch is capped at 250 KB.
- `POST /api/v1/repositories/{id}/pull-requests/{pull_request_id}/merge` attempts a non-fast-forward merge into the base branch. Git computes the merge tree first; if conflicts are detected, the API returns HTTP 409 and does not update the target branch. On success, a two-parent merge commit is created and the pull request state becomes `merged`.

The merge implementation uses `git merge-tree --write-tree` and therefore requires a Git version supporting that option (Git 2.38 or newer). Git ref update uses compare-and-swap to avoid overwriting a base branch that changed during the operation. Merge metadata is stored in a separate `pull_request_merges` table so existing pull request table schemas do not need an added column. Note that Git ref update and SQL transaction are not a distributed atomic transaction; production deployments should add reconciliation/audit handling for failures between those operations.
