from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_name: str = "SmartManager"
    app_env: str = "development"
    tz: str = "Europe/Kyiv"

    mongodb_crm_uri: str = "mongodb://localhost:27017"
    mongodb_crm_db: str = "smartzno_crm"

    jwt_secret: str = "change-me-in-production"
    jwt_ttl_min: int = 480

    crm_api_key: str = "dev-crm-api-key"
    lms_api_key: str = "dev-lms-api-key"
    lead_ingest_hmac_secret: str = "dev-lead-hmac"

    cors_origins: str = "http://localhost:3000,http://localhost:3001"

    # Telegram: notify managers about new leads / diagnostics
    telegram_bot_token: str = ""
    telegram_notify_chat_id: str = ""

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
