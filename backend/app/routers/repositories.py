from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from ..database import get_db
from ..dependencies import get_current_user
from ..git_engine import initialize_repository, list_branches, list_commits, list_files, read_file, save_file, save_file_bytes
from ..models import Repository, RepositoryMember, User
from ..schemas import FileSave, FileUpload, RepositoryCreate, RepositoryPublic

router = APIRouter(prefix="/repositories", tags=["Repositories"])

def get_owned_repository(repository_id: int, db: Session, user: User) -> Repository:
    repo = db.get(Repository, repository_id)
    if repo is None or repo.owner_id != user.id:
        raise HTTPException(status_code=404, detail="Repository not found")
    return repo

@router.post("", response_model=RepositoryPublic, status_code=status.HTTP_201_CREATED)
def create_repository(payload: RepositoryCreate, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    repo = Repository(**payload.model_dump(), owner_id=user.id)
    db.add(repo)
    try:
        db.flush()
        initialize_repository(repo)
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail="A repository with this name already exists in your account")
    except Exception:
        db.rollback()
        raise
    db.refresh(repo)
    return repo

@router.get("/mine", response_model=list[RepositoryPublic])
def list_my_repositories(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    return list(db.scalars(select(Repository).where(Repository.owner_id == user.id).order_by(Repository.created_at.desc())))

@router.get("/{repository_id}", response_model=RepositoryPublic)
def get_repository(repository_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    return get_owned_repository(repository_id, db, user)

@router.get("/{repository_id}/branches", response_model=list[str])
def get_repository_branches(repository_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    repo = get_owned_repository(repository_id, db, user)
    return list_branches(repo)

@router.get("/{repository_id}/commits")
def get_repository_commits(
    repository_id: int,
    limit: int = Query(default=20, ge=1, le=100),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    repo = get_owned_repository(repository_id, db, user)
    return list_commits(repo, limit)

@router.get("/{repository_id}/files")
def get_repository_files(
    repository_id: int,
    ref: str = Query(default="HEAD", min_length=1, max_length=200),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    repo = get_owned_repository(repository_id, db, user)
    return list_files(repo, ref)

@router.get("/{repository_id}/file")
def get_repository_file(
    repository_id: int,
    path: str = Query(min_length=1, max_length=1000),
    ref: str = Query(default="HEAD", min_length=1, max_length=200),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    repo = get_owned_repository(repository_id, db, user)
    return read_file(repo, path, ref)

from pydantic import BaseModel, Field
from ..git_engine import create_branch

class BranchCreate(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    source: str = Field(default="HEAD", min_length=1, max_length=200)

@router.post("/{repository_id}/branches", status_code=status.HTTP_201_CREATED)
def post_repository_branch(
    repository_id: int,
    payload: BranchCreate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    repo = get_owned_repository(repository_id, db, user)
    return {"name": create_branch(repo, payload.name, payload.source)}

@router.put("/{repository_id}/file")
def put_repository_file(repository_id: int, payload: FileSave, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    repo = get_owned_repository(repository_id, db, user)
    return save_file(repo, payload.branch, payload.path, payload.content, payload.message, user.username, user.email)

import base64
import binascii

@router.post("/{repository_id}/upload")
def upload_repository_file(repository_id: int, payload: FileUpload, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    repo = get_owned_repository(repository_id, db, user)
    try:
        data = base64.b64decode(payload.content_base64, validate=True)
    except (binascii.Error, ValueError):
        raise HTTPException(status_code=400, detail="Invalid base64 file content")
    if len(data) > 10 * 1024 * 1024:
        raise HTTPException(status_code=413, detail="Each uploaded file is limited to 10 MB")
    return save_file_bytes(repo, payload.branch, payload.path, data, payload.message, user.username, user.email)
