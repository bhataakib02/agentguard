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
    SECRET_KEY: str = os.getenv("SECRET_KEY", "agentguard-super-secret-production-key-2026")
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24  # 24 hours

    # Environment configuration
    ENVIRONMENT: str = os.getenv("ENVIRONMENT", "production").lower()

    # Supabase PostgreSQL Configuration
    SUPABASE_URL: str = os.getenv("SUPABASE_URL", "https://xjragvyzlailmtfwjfnm.supabase.co")
    SUPABASE_PUBLISHABLE_KEY: str = os.getenv("SUPABASE_PUBLISHABLE_KEY", "sb_publishable_ShxAT_hZy_0hMbhdceiw0A_7zB8Xjmq")

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
