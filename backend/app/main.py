from contextlib import asynccontextmanager
from fastapi import FastAPI

from .config import settings
from .database import Base, engine
from . import models  # noqa: F401 - registers SQLAlchemy models
from .routers import auth, repositories

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Convenient for the initial scaffold. Use Alembic migrations before production.
    Base.metadata.create_all(bind=engine)
    yield

app = FastAPI(title=settings.app_name, version="0.1.0", lifespan=lifespan)
app.include_router(auth.router, prefix="/api/v1")
app.include_router(repositories.router, prefix="/api/v1")

@app.get("/health", tags=["System"])
def health():
    return {"status": "ok", "service": "codeverse-api", "version": "0.1.0"}
