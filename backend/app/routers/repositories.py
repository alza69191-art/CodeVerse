from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from ..database import get_db
from ..dependencies import get_current_user
from ..models import Repository, User
from ..schemas import RepositoryCreate, RepositoryPublic

router = APIRouter(prefix="/repositories", tags=["Repositories"])

@router.post("", response_model=RepositoryPublic, status_code=status.HTTP_201_CREATED)
def create_repository(payload: RepositoryCreate, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    repo = Repository(**payload.model_dump(), owner_id=user.id)
    db.add(repo)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail="A repository with this name already exists in your account")
    db.refresh(repo)
    return repo

@router.get("/mine", response_model=list[RepositoryPublic])
def list_my_repositories(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    return list(db.scalars(select(Repository).where(Repository.owner_id == user.id).order_by(Repository.created_at.desc())))

@router.get("/{repository_id}", response_model=RepositoryPublic)
def get_repository(repository_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    repo = db.get(Repository, repository_id)
    if repo is None or repo.owner_id != user.id:
        raise HTTPException(status_code=404, detail="Repository not found")
    return repo
