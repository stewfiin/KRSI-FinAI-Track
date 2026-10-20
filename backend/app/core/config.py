from typing import Optional
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    ENV: str = "development"
    DEBUG: bool = True
    API_PORT: int = 8000
    FRONTEND_URL: str = "http://localhost:3000"
    SECRET_KEY: str = "dev_secret_finai_track_super_key_32_characters_long"

    # Database: PostgreSQL
    POSTGRES_USER: str = "finai_user"
    POSTGRES_PASSWORD: str = "finai_password"
    POSTGRES_DB: str = "KRSI-FinAI"
    POSTGRES_PORT: int = 5432
    DATABASE_URL: str = "postgresql+asyncpg://finai_user:finai_password@localhost:5432/KRSI-FinAI"

    # Cache & Broker: Redis
    REDIS_HOST: str = "localhost"
    REDIS_PORT: int = 6379
    REDIS_URL: str = "redis://localhost:6379/0"

    # Authentication & JWT
    JWT_SECRET_KEY: str = "dev_jwt_secret_finai_track_auth_signature_key_2026"
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 1440  # 24 jam

    # AI & LLM Providers
    GEMINI_API_KEY: Optional[str] = None
    GROQ_API_KEY: Optional[str] = None

    # Telegram Bot Integration
    TELEGRAM_BOT_TOKEN: Optional[str] = None
    TELEGRAM_WEBHOOK_URL: Optional[str] = None

    model_config = SettingsConfigDict(
        env_file=(".env", "../.env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )


settings = Settings()

