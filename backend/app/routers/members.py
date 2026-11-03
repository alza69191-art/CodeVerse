from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..database import get_db
from ..dependencies import get_current_user
from ..models import Repository, RepositoryMember, User
from ..schemas import MemberInvite

router = APIRouter(tags=["Repository Members"])


@router.get("/repositories/{repository_id}/members")
def list_members(repository_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    repo = db.get(Repository, repository_id)
    if repo is None:
        raise HTTPException(status_code=404, detail="Repository not found")
    if repo.owner_id != user.id:
        raise HTTPException(status_code=403, detail="Only the repository owner can manage members")
    rows = db.execute(select(RepositoryMember, User.username, User.email).join(User, User.id == RepositoryMember.user_id).where(RepositoryMember.repository_id == repository_id).order_by(RepositoryMember.created_at.desc())).all()
    return [{"id": member.id, "username": username, "email": email, "role": member.role, "status": member.status, "created_at": member.created_at} for member, username, email in rows]


@router.post("/repositories/{repository_id}/members/invite", status_code=status.HTTP_201_CREATED)
def invite_member(repository_id: int, payload: MemberInvite, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    repo = db.get(Repository, repository_id)
    if repo is None:
        raise HTTPException(status_code=404, detail="Repository not found")
    if repo.owner_id != user.id:
        raise HTTPException(status_code=403, detail="Only the repository owner can invite members")
    target = db.scalar(select(User).where(User.username == payload.username))
    if target is None:
        raise HTTPException(status_code=404, detail="User not found")
    if target.id == user.id:
        raise HTTPException(status_code=400, detail="You already own this repository")
    existing = db.scalar(select(RepositoryMember).where(RepositoryMember.repository_id == repository_id, RepositoryMember.user_id == target.id))
    if existing is not None:
        if existing.status in ("pending", "active"):
            raise HTTPException(status_code=409, detail="User is already invited or a member")
        existing.role = payload.role
        existing.status = "pending"
        existing.invited_by_id = user.id
        db.commit()
        db.refresh(existing)
        return {"id": existing.id, "username": target.username, "role": existing.role, "status": existing.status}
    member = RepositoryMember(repository_id=repository_id, user_id=target.id, invited_by_id=user.id, role=payload.role, status="pending")
    db.add(member)
    db.commit()
    db.refresh(member)
    return {"id": member.id, "username": target.username, "role": member.role, "status": member.status}


@router.get("/users/me/invitations")
def my_invitations(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    rows = db.execute(select(RepositoryMember, Repository.name, User.username).join(Repository, Repository.id == RepositoryMember.repository_id).join(User, User.id == RepositoryMember.invited_by_id).where(RepositoryMember.user_id == user.id, RepositoryMember.status == "pending").order_by(RepositoryMember.created_at.desc())).all()
    return [{"id": member.id, "repository_id": member.repository_id, "repository_name": name, "invited_by": inviter, "role": member.role, "created_at": member.created_at} for member, name, inviter in rows]


def respond_invitation(invitation_id: int, accept: bool, db: Session, user: User):
    member = db.get(RepositoryMember, invitation_id)
    if member is None or member.user_id != user.id or member.status != "pending":
        raise HTTPException(status_code=404, detail="Invitation not found")
    member.status = "active" if accept else "declined"
    db.commit()
    db.refresh(member)
    return {"id": member.id, "status": member.status, "repository_id": member.repository_id}


@router.post("/invitations/{invitation_id}/accept")
def accept_invitation(invitation_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    return respond_invitation(invitation_id, True, db, user)


@router.post("/invitations/{invitation_id}/decline")
def decline_invitation(invitation_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    return respond_invitation(invitation_id, False, db, user)


@router.put("/repositories/{repository_id}/members/{member_id}/role")
def update_member_role(repository_id: int, member_id: int, payload: MemberRoleUpdate, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    repo = db.get(Repository, repository_id)
    if repo is None:
        raise HTTPException(status_code=404, detail="Repository not found")
    if repo.owner_id != user.id:
        raise HTTPException(status_code=403, detail="Only the repository owner can manage members")
    member = db.get(RepositoryMember, member_id)
    if member is None or member.repository_id != repository_id or member.status != "active":
        raise HTTPException(status_code=404, detail="Active member not found")
    member.role = payload.role
    db.commit()
    db.refresh(member)
    return {"id": member.id, "role": member.role}


@router.delete("/repositories/{repository_id}/members/{member_id}")
def remove_member(repository_id: int, member_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    repo = db.get(Repository, repository_id)
    if repo is None:
        raise HTTPException(status_code=404, detail="Repository not found")
    if repo.owner_id != user.id:
        raise HTTPException(status_code=403, detail="Only the repository owner can manage members")
    member = db.get(RepositoryMember, member_id)
    if member is None or member.repository_id != repository_id:
        raise HTTPException(status_code=404, detail="Member not found")
    db.delete(member)
    db.commit()
    return {"deleted": True}
