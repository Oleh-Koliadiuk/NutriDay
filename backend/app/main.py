from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from .api.auth import router as auth_router
from .api.nutrition import router as nutrition_router
from .api.recipes import router as recipes_router
from .core.config import settings
from .database.base import Base
from .database.session import engine
from . import models  # noqa: F401 - register models with SQLAlchemy metadata

app = FastAPI(title=settings.project_name, version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router, prefix=settings.api_v1_prefix)
app.include_router(nutrition_router, prefix=settings.api_v1_prefix)
app.include_router(recipes_router, prefix=settings.api_v1_prefix)

BACKEND_DIR = Path(__file__).resolve().parents[1]
PROJECT_DIR = BACKEND_DIR.parent
FRONTEND_DIR = PROJECT_DIR

for asset_directory in ("js", "css", "assets"):
    asset_path = FRONTEND_DIR / asset_directory
    if asset_path.exists():
        app.mount(f"/{asset_directory}", StaticFiles(directory=str(asset_path)), name=asset_directory)


@app.on_event("startup")
def startup_event() -> None:
    Base.metadata.create_all(bind=engine)


@app.get("/health")
def health_check():
    return {"status": "ok", "project": settings.project_name}


@app.get("/", include_in_schema=False)
def index():
    index_path = FRONTEND_DIR / "index.html"
    if not index_path.exists():
        return {"message": "Frontend is not built yet"}
    return FileResponse(index_path)
