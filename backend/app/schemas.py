from datetime import datetime
from pydantic import BaseModel, ConfigDict, EmailStr, Field

class UserCreate(BaseModel):
    email: EmailStr
    username: str = Field(min_length=3, max_length=39, pattern=r"^[a-zA-Z0-9](?:[a-zA-Z0-9-]*[a-zA-Z0-9])?$")
    password: str = Field(min_length=12, max_length=128)

class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=1, max_length=128)

class UserPublic(BaseModel):
    id: int
    email: EmailStr
    username: str
    role: str
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)

class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"

class RepositoryCreate(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    slug: str = Field(min_length=1, max_length=100, pattern=r"^[a-zA-Z0-9][a-zA-Z0-9._-]*$")
    description: str = Field(default="", max_length=2000)
    is_private: bool = True

class RepositoryPublic(BaseModel):
    id: int
    name: str
    slug: str
    description: str
    is_private: bool
    default_branch: str
    owner_id: int
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)

class FileSave(BaseModel):
    path: str = Field(min_length=1, max_length=1000)
    content: str = Field(max_length=1048576)
    branch: str = Field(min_length=1, max_length=100)
    message: str = Field(min_length=1, max_length=200)

class FileUpload(BaseModel):
    path: str = Field(min_length=1, max_length=1000)
    content_base64: str = Field(min_length=1, max_length=14000000)
    branch: str = Field(min_length=1, max_length=100)
    message: str = Field(min_length=1, max_length=200)


class IssueCreate(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    body: str = Field(default="", max_length=20000)


class IssueCommentCreate(BaseModel):
    body: str = Field(min_length=1, max_length=10000)


class PullRequestCreate(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    body: str = Field(default="", max_length=20000)
    head_branch: str = Field(min_length=1, max_length=100)
    base_branch: str = Field(min_length=1, max_length=100)


class MemberInvite(BaseModel):
    username: str = Field(min_length=3, max_length=39)
    role: str = Field(default="read", pattern=r"^(read|write)$")
