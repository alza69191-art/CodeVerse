from contextlib import asynccontextmanager
from fastapi import FastAPI\nfrom fastapi.middleware.cors import CORSMiddleware

from .config import settings
from .database import Base, engine
from . import models  # noqa: F401 - registers SQLAlchemy models
from .routers import auth, git_http, repositories, tokens

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Convenient for the initial scaffold. Use Alembic migrations before production.
    Base.metadata.create_all(bind=engine)
    yield

app = FastAPI(title=settings.app_name, version="0.2.0", lifespan=lifespan)\napp.add_middleware(\n    CORSMiddleware,\n    allow_origins=[origin.strip() for origin in settings.cors_origins.split(",") if origin.strip()],\n    allow_credentials=False,\n    allow_methods=["GET", "POST", "DELETE", "OPTIONS"],\n    allow_headers=["Authorization", "Content-Type", "Git-Protocol"],\n)
app.include_router(auth.router, prefix="/api/v1")
app.include_router(tokens.router, prefix="/api/v1")
app.include_router(repositories.router, prefix="/api/v1")
app.include_router(git_http.router)

@app.get("/health", tags=["System"])
def health():
    return {"status": "ok", "service": "codeverse-api", "version": "0.2.0"}
