from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

ENV_FILE = Path(__file__).resolve().parents[2] / ".env"


class Settings(BaseSettings):
    database_url: str = (
        "postgresql+psycopg://customer_service:customer_service@192.168.100.128:5432/customer_service"
    )
    redis_url: str = "redis://192.168.100.128:6379/0"
    jwt_secret: str = "ecommerce-secret"
    jwt_algorithm: str = "HS256"
    api_host: str = "0.0.0.0"
    api_port: int = 8000
    conversation_idle_timeout: int = 60
    conversation_timeout: int = 60
    message_merge_delay_ms: int = 1500
    message_merge_max_wait_ms: int = 8000
    ai_service_url: str = "http://192.168.100.128:8002"
    internal_service_token: str = "customer-service-internal"
    ai_worker_poll_interval_ms: int = 500
    ai_worker_lease_seconds: int = 30
    ai_worker_max_attempts: int = 3
    cors_origins: list[str] = [
        "http://localhost:5173",
        "http://192.168.100.128:5173",
        "http://localhost:5174",
        "http://192.168.100.128:5174",
    ]

    model_config = SettingsConfigDict(env_file=ENV_FILE, extra="ignore")


@lru_cache
def get_settings() -> Settings:
    return Settings()
