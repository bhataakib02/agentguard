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
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24  # 24 hours

    def __init__(self):
        self.reload()

    def reload(self):
        raw_secret = os.getenv("SECRET_KEY", "").strip()
        if not raw_secret or raw_secret == "agentguard-super-secret-production-key-2026":
            import logging, secrets
            _cfg_logger = logging.getLogger("agentguard.config")
            _cfg_logger.warning("[SECURITY WARNING] SECRET_KEY is using a default or empty value. Set a secure random SECRET_KEY in production.")
            self.SECRET_KEY = raw_secret or secrets.token_hex(32)
        else:
            self.SECRET_KEY = raw_secret

        # Environment configuration
        self.ENVIRONMENT = os.getenv("ENVIRONMENT", "production").lower()

        # CORS configuration
        cors_origins_env = os.getenv("CORS_ORIGINS", "")
        if cors_origins_env:
            self.CORS_ORIGINS = [origin.strip() for origin in cors_origins_env.split(",") if origin.strip()]
        else:
            self.CORS_ORIGINS = [
                "http://localhost:3000",
                "http://127.0.0.1:3000",
                "http://localhost:8000",
                "http://127.0.0.1:8000",
                "https://agentguard.vercel.app",
            ]

        # Trusted Hosts Configuration
        trusted_hosts_env = os.getenv("TRUSTED_HOSTS", "")
        if trusted_hosts_env:
            self.TRUSTED_HOSTS = [h.strip() for h in trusted_hosts_env.split(",") if h.strip()]
        else:
            self.TRUSTED_HOSTS = ["*"] if self.ENVIRONMENT != "production" else [
                "localhost",
                "127.0.0.1",
                "testserver",
                "agentguard.vercel.app",
                "agentguard-backend.onrender.com"
            ]

        # Database Connection Pool Settings
        self.DB_POOL_SIZE = int(os.getenv("DB_POOL_SIZE", "10"))
        self.DB_MAX_OVERFLOW = int(os.getenv("DB_MAX_OVERFLOW", "20"))
        self.DB_POOL_TIMEOUT = int(os.getenv("DB_POOL_TIMEOUT", "30"))

        # Database Initialization / Migration Strategy
        self.AUTO_BOOTSTRAP_DB = os.getenv("AUTO_BOOTSTRAP_DB", "True").lower() in ("true", "1")

        # Supabase PostgreSQL Configuration
        self.SUPABASE_URL = os.getenv("SUPABASE_URL", "https://xjragvyzlailmtfwjfnm.supabase.co")
        self.SUPABASE_PUBLISHABLE_KEY = os.getenv("SUPABASE_PUBLISHABLE_KEY", "sb_publishable_ShxAT_hZy_0hMbhdceiw0A_7zB8Xjmq")
        self.SUPABASE_JWT_SECRET = os.getenv("SUPABASE_JWT_SECRET", "")

        # DATABASE_URL for Supabase PostgreSQL
        raw_db_url = os.getenv("DATABASE_URL", "").strip()

        if raw_db_url.startswith("postgres://"):
            self.DATABASE_URL = raw_db_url.replace("postgres://", "postgresql://", 1)
        elif raw_db_url.startswith("postgresql://"):
            self.DATABASE_URL = raw_db_url
        elif self.ENVIRONMENT == "production":
            raise RuntimeError(
                "[AgentGuard Configuration Error] Production environment requires a valid PostgreSQL DATABASE_URL. "
                "Silent fallback to SQLite in production is strictly prohibited."
            )
        else:
            # Explicit SQLite fallback allowed only for development/testing
            self.DATABASE_URL = os.getenv(
                "DATABASE_URL",
                f"sqlite:///{os.path.join(os.path.dirname(__file__), 'agentguard.db')}"
            )

        # -------------------------------------------------------------------------
        # PHASE 6D: Production Infrastructure Configuration
        # -------------------------------------------------------------------------
        # Redis & Celery Message Broker
        self.REDIS_URL = os.getenv("REDIS_URL", "").strip()
        self.CELERY_BROKER_URL = os.getenv("CELERY_BROKER_URL", "").strip() or self.REDIS_URL or "redis://localhost:6379/0"
        self.CELERY_RESULT_BACKEND = os.getenv("CELERY_RESULT_BACKEND", "").strip() or self.REDIS_URL or "redis://localhost:6379/0"
        raw_eager = os.getenv("CELERY_TASK_ALWAYS_EAGER", "").strip().lower()
        if raw_eager:
            self.CELERY_TASK_ALWAYS_EAGER = raw_eager in ("true", "1")
        else:
            self.CELERY_TASK_ALWAYS_EAGER = not bool(self.REDIS_URL)

        # Email / SMTP Delivery
        self.EMAIL_PROVIDER = os.getenv("EMAIL_PROVIDER", "NONE").upper()  # NONE, SMTP, MOCK
        self.SMTP_HOST = os.getenv("SMTP_HOST", "").strip()
        self.SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))
        self.SMTP_USERNAME = os.getenv("SMTP_USERNAME", "").strip()
        self.SMTP_PASSWORD = os.getenv("SMTP_PASSWORD", "").strip()
        self.SMTP_USE_TLS = os.getenv("SMTP_USE_TLS", "True").lower() in ("true", "1")
        self.SMTP_FROM_EMAIL = os.getenv("SMTP_FROM_EMAIL", "noreply@agentguard.com").strip()

        # Object / Report Storage
        self.OBJECT_STORAGE_PROVIDER = os.getenv("OBJECT_STORAGE_PROVIDER", "LOCAL").upper()  # LOCAL, S3
        self.S3_ENDPOINT = os.getenv("S3_ENDPOINT", "").strip()
        self.S3_BUCKET = os.getenv("S3_BUCKET", "").strip()
        self.S3_ACCESS_KEY = os.getenv("S3_ACCESS_KEY", "").strip()
        self.S3_SECRET_KEY = os.getenv("S3_SECRET_KEY", "").strip()
        self.S3_REGION = os.getenv("S3_REGION", "us-east-1").strip()

settings = Settings()


