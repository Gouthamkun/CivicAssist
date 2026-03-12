"""
SQLite database setup using SQLAlchemy for CivicAssist.
Stores user details and uploaded documents (Aadhaar, PAN).
"""

import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

# Database file stored in project root
DB_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "civicassist.db")
DATABASE_URL = f"sqlite:///{DB_PATH}"

engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def get_db():
    """FastAPI dependency that provides a database session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def create_tables():
    """Create all tables defined by models."""
    Base.metadata.create_all(bind=engine)
