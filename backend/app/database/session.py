from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker

from ..core.config import settings


class Base(DeclarativeBase):
    pass


database_url = settings.database_url
if database_url.startswith("sqlite:///"):
    database_path = Path(database_url.removeprefix("sqlite:///"))
    if str(database_path) != ":memory:":
        if not database_path.is_absolute():
            database_path = Path(__file__).resolve().parents[2] / database_path
        database_path.parent.mkdir(parents=True, exist_ok=True)
        # SQLite resolves relative URLs against the process working directory.
        # Normalize to the backend directory so every launch command uses one DB.
        database_url = f"sqlite:///{database_path.as_posix()}"

engine = create_engine(database_url, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
