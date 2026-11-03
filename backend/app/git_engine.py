import os
import subprocess
from pathlib import Path

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
