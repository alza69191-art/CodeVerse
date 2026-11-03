import base64
import hashlib
import hmac
import os
import subprocess
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import Response
from sqlalchemy import select
from sqlalchemy.orm import Session
from starlette.concurrency import run_in_threadpool

from ..config import settings
from ..database import get_db
from ..models import PersonalAccessToken, Repository, RepositoryMember, User

router = APIRouter(tags=["Git HTTP"])

def authenticate_basic(request: Request, db: Session) -> tuple[User, PersonalAccessToken] | None:
    header = request.headers.get("authorization", "")
    if not header.startswith("Basic "):
        return None
    try:
        decoded = base64.b64decode(header[6:], validate=True).decode("utf-8")
        username, raw_token = decoded.split(":", 1)
    except Exception:
        return None
    if not raw_token.startswith("cvp_"):
        return None
    user = db.scalar(select(User).where(User.username == username, User.is_active.is_(True)))
    if user is None:
        return None
    digest = hashlib.sha256(raw_token.encode()).hexdigest()
    records = db.scalars(select(PersonalAccessToken).where(PersonalAccessToken.user_id == user.id))
    for token in records:
        if hmac.compare_digest(token.token_hash, digest):
            return user, token
    return None

def run_git_backend(repo: Repository, git_path: str, query: str, method: str, body: bytes, content_type: str, protocol: str, remote_user: str) -> tuple[int, dict[str, str], bytes]:
    project_root = (Path(settings.repository_storage_path).resolve() / str(repo.owner_id))
    repo_path = project_root / f"{repo.id}.git"
    if not repo_path.is_dir():
        raise HTTPException(status_code=404, detail="Git repository storage not found")

    env = {
        **os.environ,
        "GIT_PROJECT_ROOT": str(project_root),
        "GIT_HTTP_EXPORT_ALL": "1",
        "GIT_CONFIG_NOSYSTEM": "1",
        "PATH_INFO": f"/{repo.id}.git/{git_path}",
        "QUERY_STRING": query,
        "REQUEST_METHOD": method,
        "CONTENT_TYPE": content_type,
        "CONTENT_LENGTH": str(len(body)),
        "GATEWAY_INTERFACE": "CGI/1.1",
        "SERVER_PROTOCOL": "HTTP/1.1",
        "REMOTE_ADDR": "127.0.0.1",
    }
    if protocol:
        env["HTTP_GIT_PROTOCOL"] = protocol
    if remote_user:
        env["REMOTE_USER"] = remote_user
        env["AUTH_TYPE"] = "Basic"

    try:
        result = subprocess.run(
            ["git", "http-backend"],
            input=body,
            capture_output=True,
            env=env,
            timeout=120,
            check=False,
        )
    except FileNotFoundError:
        raise HTTPException(status_code=503, detail="Git HTTP backend is unavailable on this server")
    except subprocess.TimeoutExpired:
        raise HTTPException(status_code=504, detail="Git operation timed out")

    raw = result.stdout
    split_at = raw.find(b"\r\n\r\n")
    delimiter = 4
    if split_at < 0:
        split_at = raw.find(b"\n\n")
        delimiter = 2
    if split_at < 0:
        raise HTTPException(status_code=502, detail="Invalid response from Git HTTP backend")

    header_blob = raw[:split_at].decode("latin-1")
    payload = raw[split_at + delimiter:]
    status_code = 200
    headers: dict[str, str] = {}
    for line in header_blob.splitlines():
        if ":" not in line:
            continue
        key, value = line.split(":", 1)
        key, value = key.strip(), value.strip()
        if key.lower() == "status":
            try:
                status_code = int(value.split(" ", 1)[0])
            except ValueError:
                status_code = 502
        elif key.lower() in {"content-type", "cache-control", "pragma", "expires"}:
            headers[key] = value
    return status_code, headers, payload

@router.api_route("/git/{repository_id}.git/{git_path:path}", methods=["GET", "POST"])
async def git_smart_http(repository_id: int, git_path: str, request: Request, db: Session = Depends(get_db)):
    repo = db.get(Repository, repository_id)
    if repo is None:
        raise HTTPException(status_code=404, detail="Repository not found")

    auth = authenticate_basic(request, db)
    service = request.query_params.get("service", "")
    is_write = service == "git-receive-pack" or git_path.endswith("git-receive-pack")
    member = None
    if auth is not None and auth[0].id != repo.owner_id:
        member = db.scalar(select(RepositoryMember).where(
            RepositoryMember.repository_id == repository_id,
            RepositoryMember.user_id == auth[0].id,
            RepositoryMember.status == "active",
        ))
    if is_write:
        allowed_role = auth is not None and (auth[0].id == repo.owner_id or (member is not None and member.role in ("write", "admin")))
        if not allowed_role or not auth[1].can_write:
            raise HTTPException(status_code=403, detail="A write-enabled token and repository write access are required")
    elif repo.is_private:
        allowed_read = auth is not None and (auth[0].id == repo.owner_id or member is not None)
        if not allowed_read or not auth[1].can_read:
            raise HTTPException(status_code=401, detail="A read-enabled token and repository access are required")

    if request.method == "POST" and git_path not in {"git-upload-pack", "git-receive-pack"}:
        raise HTTPException(status_code=404, detail="Unsupported Git service")
    if request.method == "GET" and git_path not in {"info/refs", "HEAD", "objects/info/alternates", "objects/info/http-alternates"} and not git_path.startswith(("objects/", "info/")):
        raise HTTPException(status_code=404, detail="Unsupported Git resource")

    body = await request.body()
    if len(body) > 100 * 1024 * 1024:
        raise HTTPException(status_code=413, detail="Git request exceeds the 100 MB request limit")

    status_code, headers, payload = await run_in_threadpool(
        run_git_backend,
        repo,
        git_path,
        request.url.query,
        request.method,
        body,
        request.headers.get("content-type", ""),
        request.headers.get("git-protocol", ""),
        auth[0].username if auth else "",
    )
    return Response(content=payload, status_code=status_code, headers=headers)
