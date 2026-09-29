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
    raw_db_url: str = os.getenv("DATABASE_URL", "")

    if raw_db_url.startswith("postgres://"):
        DATABASE_URL: str = raw_db_url.replace("postgres://", "postgresql://", 1)
    elif raw_db_url.startswith("postgresql://"):
        DATABASE_URL: str = raw_db_url
    else:
        # Default SQLite fallback if DATABASE_URL is not set in environment
        DATABASE_URL: str = os.getenv(
            "DATABASE_URL",
            f"sqlite:///{os.path.join(os.path.dirname(__file__), 'agentguard.db')}"
        )

settings = Settings()
