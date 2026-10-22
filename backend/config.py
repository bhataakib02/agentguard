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
        # Environment configuration
        self.ENVIRONMENT = os.getenv("ENVIRONMENT", "production").lower()

        # Git Commit Identification (Injected by Render as RENDER_GIT_COMMIT, or fallback)
        self.COMMIT_SHA = (
            os.getenv("RENDER_GIT_COMMIT", "").strip()
            or os.getenv("GIT_COMMIT_SHA", "").strip()
            or "ae95d84"
        )

        raw_secret = os.getenv("SECRET_KEY", "").strip()
        insecure_placeholders = {
            "",
            "change-this-to-a-secure-random-32-byte-hex-key",
            "agentguard-super-secret-production-key-2026",
            "agentguard-default-signing-key",
            "agentguard-dev-stable-signing-key-2026-secure",
            "agentguard-default-key-for-dev",
        }

        if self.ENVIRONMENT == "production":
            if not raw_secret or raw_secret in insecure_placeholders or len(raw_secret) < 32:
                raise RuntimeError(
                    "[AgentGuard Security Error] Production environment requires a strong, securely provisioned SECRET_KEY (minimum 32 characters). "
                    "Ephemeral key generation or insecure default keys in production are strictly prohibited."
                )
            self.SECRET_KEY = raw_secret
        else:
            # In development/testing, use a stable deterministic key if not set
            if not raw_secret or raw_secret in insecure_placeholders:
                self.SECRET_KEY = "agentguard-dev-stable-signing-key-2026-secure"
            else:
                self.SECRET_KEY = raw_secret

        # CORS configuration
        cors_origins_env = os.getenv("CORS_ORIGINS", "")
        if cors_origins_env:
            self.CORS_ORIGINS = [origin.strip() for origin in cors_origins_env.split(",") if origin.strip()]
        elif self.ENVIRONMENT == "production":
            self.CORS_ORIGINS = [
                "https://agentguard.vercel.app",
                "https://agentguard-beta-ten.vercel.app",
            ]
        else:
            self.CORS_ORIGINS = [
                "http://localhost:3000",
                "http://127.0.0.1:3000",
                "http://localhost:8000",
                "http://127.0.0.1:8000",
                "https://agentguard.vercel.app",
                "https://agentguard-beta-ten.vercel.app",
            ]
        self.CORS_ORIGIN_REGEX = os.getenv("CORS_ORIGIN_REGEX", None if self.ENVIRONMENT == "production" else r"^https://([a-zA-Z0-9_-]+\.)?vercel\.app$")

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
                "agentguard-beta-ten.vercel.app",
                "agentguard-backend.onrender.com",
                "agentguard-spfg.onrender.com",
            ]

        # Database Connection Pool Settings
        self.DB_POOL_SIZE = int(os.getenv("DB_POOL_SIZE", "10"))
        self.DB_MAX_OVERFLOW = int(os.getenv("DB_MAX_OVERFLOW", "20"))
        self.DB_POOL_TIMEOUT = int(os.getenv("DB_POOL_TIMEOUT", "30"))

        # Database Initialization / Migration Strategy
        # In production, do not run automated DDL schema migrations during web startup
        self.AUTO_BOOTSTRAP_DB = os.getenv(
            "AUTO_BOOTSTRAP_DB",
            "False" if self.ENVIRONMENT == "production" else "True"
        ).lower() in ("true", "1")

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

        # Email / SMTP / Resend Delivery
        self.EMAIL_PROVIDER = os.getenv("EMAIL_PROVIDER", "NONE").upper()  # NONE, SMTP, RESEND, MOCK
        self.RESEND_API_KEY = os.getenv("RESEND_API_KEY", "").strip()
        self.RESEND_FROM_EMAIL = os.getenv("RESEND_FROM_EMAIL", "AgentGuard <onboarding@resend.dev>").strip()
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

        # Data Governance & Retention
        self.AUDIT_LOG_RETENTION_DAYS = int(os.getenv("AUDIT_LOG_RETENTION_DAYS", "365"))
        self.TELEMETRY_RETENTION_DAYS = int(os.getenv("TELEMETRY_RETENTION_DAYS", "90"))
        self.EXPIRED_SESSION_RETENTION_DAYS = int(os.getenv("EXPIRED_SESSION_RETENTION_DAYS", "7"))

        # LLM Provider Configuration for AI Assistant & Intelligence
        self.LLM_PROVIDER = os.getenv("LLM_PROVIDER", "AUTO").upper()  # AUTO, OPENAI, ANTHROPIC, GEMINI, NONE
        self.OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "").strip()
        self.OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o-mini").strip()
        self.ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "").strip()
        self.ANTHROPIC_MODEL = os.getenv("ANTHROPIC_MODEL", "claude-3-5-sonnet-20241022").strip()
        self.GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "").strip()
        self.GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-1.5-flash").strip()

        # -------------------------------------------------------------------------
        # SIEM Log Streaming & Asynchronous Forwarder Pipeline Configuration
        # -------------------------------------------------------------------------
        self.SIEM_FORWARDER_URL = os.getenv("SIEM_FORWARDER_URL", "").strip()
        self.SIEM_AUTH_TOKEN = os.getenv("SIEM_AUTH_TOKEN", "").strip()
        self.SIEM_PROVIDER = os.getenv("SIEM_PROVIDER", "GENERIC_HTTP").upper().strip()  # GENERIC_HTTP, SPLUNK_HEC, DATADOG
        self.SIEM_FORMAT = os.getenv("SIEM_FORMAT", "JSONL").upper().strip()  # JSONL, CEF
        self.SIEM_BATCH_SIZE = int(os.getenv("SIEM_BATCH_SIZE", "100"))
        self.SIEM_TIMEOUT_SECONDS = int(os.getenv("SIEM_TIMEOUT_SECONDS", "10"))
        self.SIEM_MAX_RETRIES = int(os.getenv("SIEM_MAX_RETRIES", "3"))

        # Dedicated SIEM Provider Specific Credentials & URLs
        self.SPLUNK_HEC_URL = os.getenv("SPLUNK_HEC_URL", "").strip()
        self.SPLUNK_HEC_TOKEN = os.getenv("SPLUNK_HEC_TOKEN", "").strip()
        # -------------------------------------------------------------------------
        # External Isolated Sandbox Execution Provider Configuration
        # -------------------------------------------------------------------------
        self.SANDBOX_PROVIDER = os.getenv("SANDBOX_PROVIDER", "NOT_CONFIGURED").upper().strip()  # NOT_CONFIGURED, REMOTE_WORKER, GVISOR, FIRECRACKER, MOCK_TEST_WORKER
        self.SANDBOX_ENDPOINT_URL = os.getenv("SANDBOX_ENDPOINT_URL", "").strip()
        self.SANDBOX_API_KEY = os.getenv("SANDBOX_API_KEY", "").strip()
        self.SANDBOX_DEFAULT_TIMEOUT_SECONDS = int(os.getenv("SANDBOX_DEFAULT_TIMEOUT_SECONDS", "30"))
        self.SANDBOX_MAX_MEMORY_MB = int(os.getenv("SANDBOX_MAX_MEMORY_MB", "512"))
        self.SANDBOX_MAX_CPU_CORES = float(os.getenv("SANDBOX_MAX_CPU_CORES", "1.0"))
        self.SANDBOX_MAX_PROCESSES = int(os.getenv("SANDBOX_MAX_PROCESSES", "32"))
        self.SANDBOX_MAX_OUTPUT_SIZE_BYTES = int(os.getenv("SANDBOX_MAX_OUTPUT_SIZE_BYTES", "65536"))  # 64 KB
        self.SANDBOX_ALLOW_NETWORK = os.getenv("SANDBOX_ALLOW_NETWORK", "False").lower() in ("true", "1")
        self.SANDBOX_ARTIFACT_RETENTION_HOURS = int(os.getenv("SANDBOX_ARTIFACT_RETENTION_HOURS", "24"))

settings = Settings()



