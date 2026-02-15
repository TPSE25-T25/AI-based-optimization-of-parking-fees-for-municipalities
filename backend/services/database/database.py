import os
from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

# Default: local SQLite file in backend/db/app.db
BASE_DIR = Path(__file__).resolve().parent
DEFAULT_SQLITE_URL = f"sqlite:///{BASE_DIR / 'app.db'}"
DATABASE_URL = os.getenv("DATABASE_URL", DEFAULT_SQLITE_URL)

engine = create_engine(DATABASE_URL, echo=False, future=True)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)
Base = declarative_base()
