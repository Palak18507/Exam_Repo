from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from config import DATABASE_URL

engine = create_engine(DATABASE_URL, pool_size=5, max_overflow=10)
SessionLocal = sessionmaker(bind=engine)
Base = declarative_base()


def init_db():
    """Create all tables if they don't exist."""
    from db.models import ExamPaper, PaperMetadata, Question, Subpart  # noqa: F401
    Base.metadata.create_all(bind=engine)


def get_session():
    """Get a new database session."""
    return SessionLocal()
