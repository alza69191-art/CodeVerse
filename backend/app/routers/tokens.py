import hashlib
import secrets
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..database import get_db
from ..dependencies import get_current_user
from ..models import PersonalAccessToken, User

router = APIRouter(prefix="/tokens", tags=["Personal access tokens"])

class TokenCreate(BaseModel):
    name: str = Field(min_length=1, max_length=80)
    can_read: bool = True
    can_write: bool = False

class TokenCreated(BaseModel):
    id: int
    name: str
    token: str
    can_read: bool
    can_write: bool

class TokenPublic(BaseModel):
    id: int
    name: str
    can_read: bool
    can_write: bool
    created_at: str

@router.post("", response_model=TokenCreated, status_code=status.HTTP_201_CREATED)
def create_token(payload: TokenCreate, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    if not payload.can_read and not payload.can_write:
        raise HTTPException(status_code=422, detail="At least one permission must be enabled")
    raw_token = "cvp_" + secrets.token_urlsafe(32)
    record = PersonalAccessToken(
        user_id=user.id,
        name=payload.name,
        token_hash=hashlib.sha256(raw_token.encode()).hexdigest(),
        can_read=payload.can_read or payload.can_write,
        can_write=payload.can_write,
    )
    db.add(record)
    db.commit()
    db.refresh(record)
    return TokenCreated(id=record.id, name=record.name, token=raw_token, can_read=record.can_read, can_write=record.can_write)

@router.get("", response_model=list[TokenPublic])
def list_tokens(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    records = db.scalars(select(PersonalAccessToken).where(PersonalAccessToken.user_id == user.id).order_by(PersonalAccessToken.created_at.desc()))
    return [TokenPublic(id=t.id, name=t.name, can_read=t.can_read, can_write=t.can_write, created_at=t.created_at.isoformat()) for t in records]

@router.delete("/{token_id}", status_code=status.HTTP_204_NO_CONTENT)
def revoke_token(token_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    record = db.get(PersonalAccessToken, token_id)
    if record is None or record.user_id != user.id:
        raise HTTPException(status_code=404, detail="Token not found")
    db.delete(record)
    db.commit()
    return None
