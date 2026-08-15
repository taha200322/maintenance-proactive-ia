"""
Application Configuration

Uses pydantic-settings to load config from environment variables and .env file.
Every setting has a sensible default for local development.

For production: override via environment variables or .env file.
Never hardcode secrets — use .env (which is in .gitignore).
"""

from pydantic_settings import BaseSettings, SettingsConfigDict
from functools import lru_cache


class Settings(BaseSettings):
    """
    Central configuration for the entire application.
    
    All values can be overridden via environment variables.
    Example: DATABASE_URL=postgres://user:pass@host:5432/db uvicorn ...
    """
    
    # --- Application ---
    APP_NAME: str = "Maintenance Proactif API"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = True
    API_V1_PREFIX: str = "/api/v1"
    
    # --- Database ---
    # Format: postgresql+asyncpg://user:password@host:port/dbname
    DATABASE_URL: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/proactive_maintenance"
    DATABASE_ECHO: bool = False  # Set True to log all SQL queries (debugging)
    
    # --- JWT Authentication ---
    SECRET_KEY: str = "CHANGE-ME-IN-PRODUCTION-never-use-this-default-key"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24  # 24 hours
    
    # --- Agent Authentication ---
    # Agents authenticate via API keys. We verify against hashed keys in DB.
    
    # --- CORS (Frontend) ---
    CORS_ORIGINS: list[str] = ["http://localhost:3000", "http://127.0.0.1:3000"]
    
    # --- Metrics Collection ---
    DEFAULT_COLLECTION_INTERVAL: int = 60  # seconds
    
    # --- AI/ML ---
    ANOMALY_CONTAMINATION: float = 0.1  # Expected anomaly proportion (10%)
    AI_MODEL_PATH: str = "models/isolation_forest_v1.joblib"
    HEALTH_SCORE_WEIGHTS: dict = {
        "cpu": 0.25,
        "ram": 0.25,
        "disk": 0.20,
        "temperature": 0.15,
        "anomaly": 0.15,
    }
    
    # --- Email (optional, for notifications) ---
    SMTP_HOST: str = ""
    SMTP_PORT: int = 587
    SMTP_USER: str = ""
    SMTP_PASSWORD: str = ""
    SMTP_FROM: str = ""
    SMTP_TLS: bool = True
    EMAIL_ENABLED: bool = False
    
    # --- Data Retention ---
    METRICS_RETENTION_DAYS: int = 30
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
    )


@lru_cache()
def get_settings() -> Settings:
    """
    Cached settings instance.
    lru_cache ensures we only read .env once per process.
    """
    return Settings()
