import logging

from sqlalchemy import create_engine, text
from sqlalchemy.orm import declarative_base, sessionmaker
from sqlalchemy.pool import StaticPool

from src.infrastructure.settings import settings

logger = logging.getLogger(__name__)


def build_engine():
    database_url = settings.database_url
    try:
        engine = create_engine(database_url)
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))
        return engine
    except Exception:
        if database_url.startswith("postgres"):
            logger.warning(
                "PostgreSQL is unavailable; using the local SQLite database for this run."
            )
            sqlite_url = "sqlite:///./greenhouse.db"
            return create_engine(
                sqlite_url,
                connect_args={"check_same_thread": False},
                poolclass=StaticPool,
            )
        raise


engine = build_engine()
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()