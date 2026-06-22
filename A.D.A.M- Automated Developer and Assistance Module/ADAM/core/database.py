"""SQLAlchemy-based database engine and session factory."""
from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from ADAM.core.config import get_settings


class Base(DeclarativeBase):
    pass


_engine = None
_SessionLocal = None


def get_engine():
    global _engine
    if _engine is None:
        settings = get_settings()
        _engine = create_engine(
            f"sqlite:///{settings.db_path}",
            connect_args={"check_same_thread": False},
            echo=settings.debug,
        )
    return _engine


def get_session_factory():
    global _SessionLocal
    if _SessionLocal is None:
        _SessionLocal = sessionmaker(
            bind=get_engine(),
            class_=Session,
            autoflush=False,
            autocommit=False,
            expire_on_commit=False,
        )
    return _SessionLocal


def get_db() -> Session:
    """Yield a database session (FastAPI dependency)."""
    factory = get_session_factory()
    db = factory()
    try:
        yield db
    finally:
        db.close()


def init_db() -> None:
    """Create all tables."""
    Base.metadata.create_all(bind=get_engine())
