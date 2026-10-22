from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from config import settings

connect_args = {}
if settings.DATABASE_URL.startswith("sqlite"):
    connect_args = {"check_same_thread": False}
else:
    connect_args = {"options": "-c search_path=public,extensions"}

engine_kwargs = {
    "connect_args": connect_args,
    "pool_pre_ping": True,
    "pool_recycle": 300,
    "echo": False
}
if not settings.DATABASE_URL.startswith("sqlite"):
    engine_kwargs.update({
        "pool_size": getattr(settings, "DB_POOL_SIZE", 10),
        "max_overflow": getattr(settings, "DB_MAX_OVERFLOW", 20),
        "pool_timeout": getattr(settings, "DB_POOL_TIMEOUT", 30)
    })

def validate_test_database_target(db_url: str):
    """
    Guarantees test executions only use dedicated disposable test databases.
    Fails closed immediately if a test environment attempts to connect to
    production, staging, or remote Supabase hosts.
    """
    import os, sys
    is_test_env = (
        os.getenv("ENVIRONMENT") in ("testing", "test")
        or "pytest" in sys.modules
        or "PYTEST_CURRENT_TEST" in os.environ
    )
    if is_test_env:
        db_url_lower = db_url.lower()
        forbidden_targets = [
            "supabase.co",
            "pooler.supabase.com",
            "aws-0-",
            "agentguard-prod",
            "db.agentguard.io"
        ]
        for forbidden in forbidden_targets:
            if forbidden in db_url_lower and not db_url_lower.startswith("sqlite"):
                raise RuntimeError(
                    f"[AgentGuard Test Isolation Guard] Test runner attempted connection to non-test target: '{forbidden}'. "
                    "Automated tests must run exclusively against isolated, disposable test databases. "
                    "Halting execution to prevent database pollution."
                )

validate_test_database_target(settings.DATABASE_URL)

engine = create_engine(settings.DATABASE_URL, **engine_kwargs)

if settings.DATABASE_URL.startswith("sqlite"):
    from sqlalchemy import event
    @event.listens_for(engine, "connect")
    def set_sqlite_pragma(dbapi_connection, connection_record):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
