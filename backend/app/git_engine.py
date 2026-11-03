import os
import subprocess
import tempfile
from pathlib import Path, PurePosixPath

from fastapi import HTTPException

from .config import settings
from .models import Repository

def repository_path(repo: Repository) -> Path:
    # Use numeric database IDs, never user-controlled names, in filesystem paths.
    return Path(settings.repository_storage_path).resolve() / str(repo.owner_id) / f"{repo.id}.git"

def _git(path: Path, *args: str) -> str:
    try:
        result = subprocess.run(
            ["git", "--git-dir", str(path), *args],
            check=True,
            capture_output=True,
            text=True,
            timeout=20,
            env={**os.environ, "GIT_CONFIG_NOSYSTEM": "1"},
        )
        return result.stdout
    except FileNotFoundError:
        raise HTTPException(status_code=503, detail="Git is not installed on the API server")
    except subprocess.TimeoutExpired:
        raise HTTPException(status_code=504, detail="Git operation timed out")
    except subprocess.CalledProcessError:
        raise HTTPException(status_code=500, detail="Git operation failed")

def initialize_repository(repo: Repository) -> str:
    path = repository_path(repo)
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        raise HTTPException(status_code=409, detail="Git storage already exists for this repository")
    try:
        subprocess.run(
            ["git", "init", "--bare", "--initial-branch=main", str(path)],
            check=True, capture_output=True, text=True, timeout=20,
        )
    except FileNotFoundError:
        raise HTTPException(status_code=503, detail="Git is not installed on the API server")
    except (subprocess.CalledProcessError, subprocess.TimeoutExpired):
        raise HTTPException(status_code=500, detail="Could not initialize Git repository")
    return str(path)

def list_branches(repo: Repository) -> list[str]:
    path = repository_path(repo)
    if not path.is_dir():
        raise HTTPException(status_code=404, detail="Git repository storage not found")
    output = _git(path, "for-each-ref", "--format=%(refname:short)", "refs/heads")
    return [line for line in output.splitlines() if line]

def list_commits(repo: Repository, limit: int = 20) -> list[dict]:
    path = repository_path(repo)
    if not path.is_dir():
        raise HTTPException(status_code=404, detail="Git repository storage not found")
    fmt = "%H%x1f%an%x1f%ae%x1f%aI%x1f%s"
    output = _git(path, "log", "--all", f"--max-count={limit}", f"--format={fmt}")
    commits = []
    for line in output.splitlines():
        parts = line.split("\x1f", 4)
        if len(parts) == 5:
            commits.append({"sha": parts[0], "author": parts[1], "email": parts[2], "date": parts[3], "message": parts[4]})
    return commits

def list_files(repo: Repository, ref: str = "HEAD") -> list[dict]:
    path = repository_path(repo)
    if not path.is_dir():
        raise HTTPException(status_code=404, detail="Git repository storage not found")
    commit = _git(path, "rev-parse", "--verify", "--end-of-options", ref + "^{commit}").strip()
    output = _git(path, "ls-tree", "-r", "-z", "--name-only", commit)
    return [{"path": item, "type": "file"} for item in output.split("\0") if item]

def read_file(repo: Repository, file_path: str, ref: str = "HEAD") -> dict:
    import posixpath
    normalized = _validate_file_path(file_path)
    path = repository_path(repo)
    if not path.is_dir():
        raise HTTPException(status_code=404, detail="Git repository storage not found")
    commit = _git(path, "rev-parse", "--verify", "--end-of-options", ref + "^{commit}").strip()
    try:
        result = subprocess.run(
            ["git", "--git-dir", str(path), "show", commit + ":" + normalized],
            capture_output=True, timeout=20,
            env={**os.environ, "GIT_CONFIG_NOSYSTEM": "1"},
        )
    except subprocess.TimeoutExpired:
        raise HTTPException(status_code=504, detail="Git operation timed out")
    if result.returncode != 0:
        raise HTTPException(status_code=404, detail="File not found in this revision")
    if len(result.stdout) > 1048576:
        raise HTTPException(status_code=413, detail="File exceeds the 1 MB preview limit")
    try:
        content = result.stdout.decode("utf-8")
    except UnicodeDecodeError:
        raise HTTPException(status_code=415, detail="Binary files cannot be previewed as text")
    return {"path": normalized, "ref": ref, "size": len(result.stdout), "content": content}

def _validate_file_path(file_path: str) -> str:
    if not file_path or "\x00" in file_path or "\\" in file_path or file_path.startswith("/"):
        raise HTTPException(status_code=400, detail="Invalid file path")
    parts = file_path.split("/")
    if any(part in {"", ".", ".."} or part.lower() == ".git" for part in parts) or len(file_path.encode("utf-8")) > 1000:
        raise HTTPException(status_code=400, detail="Invalid file path")
    return str(PurePosixPath(file_path))

def create_branch(repo: Repository, branch_name: str, source_ref: str = "HEAD") -> str:
    path = repository_path(repo)
    if not path.is_dir():
        raise HTTPException(status_code=404, detail="Git repository storage not found")
    try:
        subprocess.run(["git", "--git-dir", str(path), "check-ref-format", "--branch", branch_name], check=True, capture_output=True, timeout=10, env={**os.environ, "GIT_CONFIG_NOSYSTEM": "1"})
        commit = _git(path, "rev-parse", "--verify", "--end-of-options", source_ref + "^{commit}").strip()
        _git(path, "branch", branch_name, commit)
    except subprocess.CalledProcessError:
        raise HTTPException(status_code=409, detail="Invalid branch name, missing source commit, or branch already exists")
    except subprocess.TimeoutExpired:
        raise HTTPException(status_code=504, detail="Git operation timed out")
    return branch_name

def save_file(repo: Repository, branch: str, file_path: str, content: str, message: str, author_name: str, author_email: str) -> dict:
    return save_file_bytes(repo, branch, file_path, content.encode("utf-8"), message, author_name, author_email)

def save_file_bytes(repo: Repository, branch: str, file_path: str, data: bytes, message: str, author_name: str, author_email: str) -> dict:
    normalized = _validate_file_path(file_path)
    if len(data) > 1048576:
        raise HTTPException(status_code=413, detail="Files are limited to 1 MB")
    if not message.strip() or len(message) > 200:
        raise HTTPException(status_code=400, detail="Commit message must be 1-200 characters")
    if not branch or len(branch) > 100:
        raise HTTPException(status_code=400, detail="Invalid branch")
    path = repository_path(repo)
    if not path.is_dir():
        raise HTTPException(status_code=404, detail="Git repository storage not found")
    env = {**os.environ, "GIT_CONFIG_NOSYSTEM": "1"}
    try:
        subprocess.run(["git", "--git-dir", str(path), "check-ref-format", "--branch", branch], check=True, capture_output=True, timeout=10, env=env)
    except (subprocess.CalledProcessError, subprocess.TimeoutExpired):
        raise HTTPException(status_code=400, detail="Invalid branch name")
    ref = "refs/heads/" + branch
    try:
        current = subprocess.run(["git", "--git-dir", str(path), "rev-parse", "--verify", "--quiet", ref], capture_output=True, text=True, timeout=10, env=env)
    except subprocess.TimeoutExpired:
        raise HTTPException(status_code=504, detail="Git operation timed out")
    if current.returncode not in (0, 1):
        raise HTTPException(status_code=500, detail="Could not resolve target branch")
    old_commit = current.stdout.strip() if current.returncode == 0 else None
    if old_commit is None and branch != repo.default_branch:
        raise HTTPException(status_code=404, detail="Branch not found")
    fd, index_path = tempfile.mkstemp(prefix="codeverse-index-")
    os.close(fd)
    os.unlink(index_path)
    env["GIT_INDEX_FILE"] = index_path

    def run(args, input_data=None, text_mode=True):
        try:
            return subprocess.run(["git", "--git-dir", str(path), *args], input=input_data, check=True, capture_output=True, text=text_mode, timeout=30, env=env)
        except subprocess.CalledProcessError:
            raise HTTPException(status_code=409, detail="Git rejected the save; refresh the branch and retry")
        except subprocess.TimeoutExpired:
            raise HTTPException(status_code=504, detail="Git operation timed out")

    try:
        run(["read-tree", old_commit] if old_commit else ["read-tree", "--empty"])
        blob = run(["hash-object", "-w", "--stdin"], data, False).stdout.decode().strip()
        run(["update-index", "--add", "--cacheinfo", "100644", blob, normalized])
        tree = run(["write-tree"]).stdout.strip()
        identity = author_name.replace("\n", " ").replace("\r", " ")[:100] or "CodeVerse User"
        email = author_email.replace("\n", "").replace("\r", "")[:254] or "noreply@codeverse.local"
        commit_env = {**env, "GIT_AUTHOR_NAME": identity, "GIT_AUTHOR_EMAIL": email, "GIT_COMMITTER_NAME": identity, "GIT_COMMITTER_EMAIL": email}
        args = ["git", "--git-dir", str(path), "commit-tree", tree]
        if old_commit:
            args.extend(["-p", old_commit])
        args.extend(["-m", message.strip()])
        created = subprocess.run(args, check=True, capture_output=True, text=True, timeout=30, env=commit_env).stdout.strip()
        expected = old_commit or ("0" * 40)
        subprocess.run(["git", "--git-dir", str(path), "update-ref", ref, created, expected], check=True, capture_output=True, text=True, timeout=15, env=env)
        return {"commit": created, "branch": branch, "path": normalized}
    except subprocess.CalledProcessError:
        raise HTTPException(status_code=409, detail="Branch changed during save or Git rejected the update; refresh and retry")
    except subprocess.TimeoutExpired:
        raise HTTPException(status_code=504, detail="Git operation timed out")
    finally:
        try:
            os.unlink(index_path)
        except FileNotFoundError:
            pass
