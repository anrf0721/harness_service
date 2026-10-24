"""
author: anrf
date:9/18/2026
desc:
"""
from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

ENV_FILE = Path(__file__).resolve().parents[2] / ".env"


class Settings(BaseSettings):
    database_url: str = (
        "postgresql+psycopg://customer_service:customer_service@192.168.100.128:5432/ai_service"
    )
    ecommerce_service_url: str = "http://127.0.0.1:8001/api/v1"
    jwt_secret: str = "ecommerce-secret"
    jwt_algorithm: str = "HS256"
    api_host: str = "0.0.0.0"
    api_port: int = 8002
    internal_service_token: str = "customer-service-internal"
    llm_model: str = ""
    prompt_version: str = "customer-support-v1"
    llm_api_key: str = ""
    llm_base_url: str | None = None
    llm_provider: str = "openai"
    llm_timeout_seconds: int = 60
    # LLM_PROVIDER=local 时，ChatOpenAI 改打训练后的本地 OpenAI 兼容接口。
    local_model_base_url: str = "http://127.0.0.1:8003/v1"
    local_served_model: str = "customer-support-grpo"
    history_message_limit: int = 30
    history_character_budget: int = 12000
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
