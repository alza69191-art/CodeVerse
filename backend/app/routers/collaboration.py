from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..database import get_db
from ..dependencies import get_current_user
from ..git_engine import list_branches
from ..models import Issue, IssueComment, PullRequest, Repository, User
from ..schemas import IssueCreate, IssueCommentCreate, PullRequestCreate

router = APIRouter(prefix="/repositories/{repository_id}", tags=["Collaboration"])


def owned_repo(repository_id: int, db: Session, user: User) -> Repository:
    repo = db.get(Repository, repository_id)
    if repo is None or repo.owner_id != user.id:
        raise HTTPException(status_code=404, detail="Repository not found")
    return repo


def issue_or_404(issue_id: int, repository_id: int, db: Session) -> Issue:
    issue = db.get(Issue, issue_id)
    if issue is None or issue.repository_id != repository_id:
        raise HTTPException(status_code=404, detail="Issue not found")
    return issue


@router.get("/issues")
def list_issues(repository_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    owned_repo(repository_id, db, user)
    return list(db.scalars(select(Issue).where(Issue.repository_id == repository_id).order_by(Issue.created_at.desc())))


@router.post("/issues", status_code=status.HTTP_201_CREATED)
def create_issue(repository_id: int, payload: IssueCreate, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    owned_repo(repository_id, db, user)
    issue = Issue(repository_id=repository_id, author_id=user.id, title=payload.title, body=payload.body)
    db.add(issue)
    db.commit()
    db.refresh(issue)
    return issue


@router.get("/issues/{issue_id}")
def get_issue(repository_id: int, issue_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    owned_repo(repository_id, db, user)
    issue = issue_or_404(issue_id, repository_id, db)
    comments = list(db.scalars(select(IssueComment).where(IssueComment.issue_id == issue_id).order_by(IssueComment.created_at.asc())))
    return {"issue": issue, "comments": comments}


@router.post("/issues/{issue_id}/comments", status_code=status.HTTP_201_CREATED)
def add_issue_comment(repository_id: int, issue_id: int, payload: IssueCommentCreate, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    owned_repo(repository_id, db, user)
    issue = issue_or_404(issue_id, repository_id, db)
    if issue.state != "open":
        raise HTTPException(status_code=409, detail="Cannot comment on a closed issue")
    comment = IssueComment(issue_id=issue_id, author_id=user.id, body=payload.body)
    db.add(comment)
    db.commit()
    db.refresh(comment)
    return comment


@router.post("/issues/{issue_id}/close")
def close_issue(repository_id: int, issue_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    owned_repo(repository_id, db, user)
    issue = issue_or_404(issue_id, repository_id, db)
    issue.state = "closed"
    db.commit()
    db.refresh(issue)
    return issue


@router.get("/pull-requests")
def list_pull_requests(repository_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    owned_repo(repository_id, db, user)
    return list(db.scalars(select(PullRequest).where(PullRequest.repository_id == repository_id).order_by(PullRequest.created_at.desc())))


@router.post("/pull-requests", status_code=status.HTTP_201_CREATED)
def create_pull_request(repository_id: int, payload: PullRequestCreate, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    repo = owned_repo(repository_id, db, user)
    if payload.head_branch == payload.base_branch:
        raise HTTPException(status_code=400, detail="Head and base branches must be different")
    branches = set(list_branches(repo))
    if payload.head_branch not in branches or payload.base_branch not in branches:
        raise HTTPException(status_code=400, detail="Both branches must exist in this repository")
    pr = PullRequest(repository_id=repository_id, author_id=user.id, **payload.model_dump())
    db.add(pr)
    db.commit()
    db.refresh(pr)
    return pr


@router.post("/pull-requests/{pull_request_id}/close")
def close_pull_request(repository_id: int, pull_request_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    owned_repo(repository_id, db, user)
    pr = db.get(PullRequest, pull_request_id)
    if pr is None or pr.repository_id != repository_id:
        raise HTTPException(status_code=404, detail="Pull request not found")
    pr.state = "closed"
    db.commit()
    db.refresh(pr)
    return pr
