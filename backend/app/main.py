from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .config import settings
from .database import Base, engine
from . import models  # noqa: F401 - registers SQLAlchemy models
from .routers import auth, collaboration, git_http, members, repositories, tokens


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Convenient for the initial scaffold. Use Alembic migrations before production.
    Base.metadata.create_all(bind=engine)
    yield


app = FastAPI(title=settings.app_name, version="0.3.0", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[origin.strip() for origin in settings.cors_origins.split(",") if origin.strip()],
    allow_credentials=False,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type", "Git-Protocol"],
)
app.include_router(auth.router, prefix="/api/v1")
app.include_router(tokens.router, prefix="/api/v1")
app.include_router(repositories.router, prefix="/api/v1")
app.include_router(collaboration.router, prefix="/api/v1")
app.include_router(members.router, prefix="/api/v1")
app.include_router(git_http.router)


@app.get("/health", tags=["System"])
def health():
    return {"status": "ok", "service": "codeverse-api", "version": "0.3.0"}
