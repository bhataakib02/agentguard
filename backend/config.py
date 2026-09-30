import os
from dotenv import load_dotenv

# Load environment variables from .env if present
env_path = os.path.join(os.path.dirname(__file__), ".env")
if os.path.exists(env_path):
    load_dotenv(env_path)

class Settings:
    PROJECT_NAME: str = "AGENTGUARD"
    TAGLINE: str = "Runtime Control Plane for Autonomous AI"
    API_V1_STR: str = "/api"
    raw_secret: str = os.getenv("SECRET_KEY", "").strip()
    if not raw_secret or raw_secret == "agentguard-super-secret-production-key-2026":
        import logging, secrets
        _cfg_logger = logging.getLogger("agentguard.config")
        _cfg_logger.warning("[SECURITY WARNING] SECRET_KEY is using a default or empty value. Set a secure random SECRET_KEY in production.")
        SECRET_KEY: str = raw_secret or secrets.token_hex(32)
    else:
        SECRET_KEY: str = raw_secret

    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24  # 24 hours

    # Environment configuration
    ENVIRONMENT: str = os.getenv("ENVIRONMENT", "production").lower()

    # CORS configuration
    cors_origins_env: str = os.getenv("CORS_ORIGINS", "")
    if cors_origins_env:
        CORS_ORIGINS: list = [origin.strip() for origin in cors_origins_env.split(",") if origin.strip()]
    else:
        CORS_ORIGINS: list = [
            "http://localhost:3000",
            "http://127.0.0.1:3000",
            "http://localhost:8000",
            "http://127.0.0.1:8000",
            "https://agentguard.vercel.app",
        ]

    # Supabase PostgreSQL Configuration
    SUPABASE_URL: str = os.getenv("SUPABASE_URL", "https://xjragvyzlailmtfwjfnm.supabase.co")
    SUPABASE_PUBLISHABLE_KEY: str = os.getenv("SUPABASE_PUBLISHABLE_KEY", "sb_publishable_ShxAT_hZy_0hMbhdceiw0A_7zB8Xjmq")
    SUPABASE_JWT_SECRET: str = os.getenv("SUPABASE_JWT_SECRET", "")

    # DATABASE_URL for Supabase PostgreSQL
    raw_db_url: str = os.getenv("DATABASE_URL", "").strip()

    if raw_db_url.startswith("postgres://"):
        DATABASE_URL: str = raw_db_url.replace("postgres://", "postgresql://", 1)
    elif raw_db_url.startswith("postgresql://"):
        DATABASE_URL: str = raw_db_url
    elif ENVIRONMENT == "production":
        raise RuntimeError(
            "[AgentGuard Configuration Error] Production environment requires a valid PostgreSQL DATABASE_URL. "
            "Silent fallback to SQLite in production is strictly prohibited."
        )
    else:
        # Explicit SQLite fallback allowed only for development/testing
        DATABASE_URL: str = os.getenv(
            "DATABASE_URL",
            f"sqlite:///{os.path.join(os.path.dirname(__file__), 'agentguard.db')}"
        )

    # -------------------------------------------------------------------------
    # PHASE 6D: Production Infrastructure Configuration
    # -------------------------------------------------------------------------
    # Redis & Celery Message Broker
    REDIS_URL: str = os.getenv("REDIS_URL", "").strip()
    CELERY_BROKER_URL: str = os.getenv("CELERY_BROKER_URL", "").strip() or REDIS_URL or "redis://localhost:6379/0"
    CELERY_RESULT_BACKEND: str = os.getenv("CELERY_RESULT_BACKEND", "").strip() or REDIS_URL or "redis://localhost:6379/0"
    raw_eager = os.getenv("CELERY_TASK_ALWAYS_EAGER", "").strip().lower()
    if raw_eager:
        CELERY_TASK_ALWAYS_EAGER: bool = raw_eager in ("true", "1")
    else:
        # Default eager to True if REDIS_URL is not set (e.g. testing / local without Redis daemon)
        CELERY_TASK_ALWAYS_EAGER: bool = not bool(REDIS_URL)


    # Email / SMTP Delivery
    EMAIL_PROVIDER: str = os.getenv("EMAIL_PROVIDER", "NONE").upper()  # NONE, SMTP, MOCK
    SMTP_HOST: str = os.getenv("SMTP_HOST", "").strip()
    SMTP_PORT: int = int(os.getenv("SMTP_PORT", "587"))
    SMTP_USERNAME: str = os.getenv("SMTP_USERNAME", "").strip()
    SMTP_PASSWORD: str = os.getenv("SMTP_PASSWORD", "").strip()
    SMTP_USE_TLS: bool = os.getenv("SMTP_USE_TLS", "True").lower() in ("true", "1")
    SMTP_FROM_EMAIL: str = os.getenv("SMTP_FROM_EMAIL", "noreply@agentguard.com").strip()

    # Object / Report Storage
    OBJECT_STORAGE_PROVIDER: str = os.getenv("OBJECT_STORAGE_PROVIDER", "LOCAL").upper()  # LOCAL, S3
    S3_ENDPOINT: str = os.getenv("S3_ENDPOINT", "").strip()
    S3_BUCKET: str = os.getenv("S3_BUCKET", "").strip()
    S3_ACCESS_KEY: str = os.getenv("S3_ACCESS_KEY", "").strip()
    S3_SECRET_KEY: str = os.getenv("S3_SECRET_KEY", "").strip()
    S3_REGION: str = os.getenv("S3_REGION", "us-east-1").strip()

settings = Settings()

