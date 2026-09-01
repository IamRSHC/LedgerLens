from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker
from app.config import settings

connect_args = {"check_same_thread": False} if "sqlite" in settings.database_url else {}
engine = create_engine(settings.database_url, connect_args=connect_args)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def create_tables():
    from app.models import models  # noqa
    Base.metadata.create_all(bind=engine)
    _ensure_provenance_columns()


def _ensure_provenance_columns():
    """
    Step 7.2 backwards-compat: `ai_investigations` gains three provenance
    columns (`provider`, `model`, `fallback_reason`). SQLAlchemy's create_all
    only creates missing TABLES, not missing COLUMNS on an existing table —
    so on a demo DB carried over from earlier steps, we ALTER TABLE.
    Idempotent: silently skips columns that already exist.
    """
    for col, ddl in (
        ("provider",        "TEXT"),
        ("model",           "TEXT"),
        ("fallback_reason", "TEXT"),
    ):
        try:
            with engine.begin() as conn:
                conn.exec_driver_sql(
                    f"ALTER TABLE ai_investigations ADD COLUMN {col} {ddl}"
                )
        except Exception:
            # SQLite raises OperationalError ("duplicate column name") when the
            # column already exists — that's fine, this is a compat backfill.
            pass
