import logging

from sqlalchemy import create_engine, inspect, text
from sqlalchemy.orm import DeclarativeBase, sessionmaker

from server.config import Settings

logger = logging.getLogger("ask-michal")

settings = Settings()
engine = create_engine(
    settings.database_url,
    connect_args={"check_same_thread": False},
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


class Base(DeclarativeBase):
    pass


def get_db():
    """FastAPI dependency for database sessions."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def _migrate_rating_columns():
    """Add rating columns to query_logs if they don't exist (SQLite migration)."""
    inspector = inspect(engine)
    existing = {col["name"] for col in inspector.get_columns("query_logs")}
    migrations = {
        "rating": "INTEGER",
        "rating_comment": "TEXT",
        "rated_at": "DATETIME",
    }
    with engine.begin() as conn:
        for col_name, col_type in migrations.items():
            if col_name not in existing:
                conn.execute(text(
                    f"ALTER TABLE query_logs ADD COLUMN {col_name} {col_type}"
                ))
                logger.info(f"Migrated: added column query_logs.{col_name}")


def init_db():
    """Create all tables."""
    Base.metadata.create_all(bind=engine)
    try:
        _migrate_rating_columns()
    except Exception:
        pass
