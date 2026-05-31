from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Runtime configuration loaded from environment variables."""

    app_env: str = "local"
    database_url: str = "sqlite+pysqlite:///./trading_system.db"
    kis_app_key: str = ""
    kis_app_secret: str = ""
    kis_account_no: str = ""
    kis_base_url: str = "https://openapi.koreainvestment.com:9443"
    telegram_bot_token: str = ""
    telegram_chat_id: str = ""
    rebalance_cron_hour: int = 15
    rebalance_cron_minute: int = 40
    fee_rate: float = 0.00015
    slippage_rate: float = 0.001
    sell_tax_rate: float = 0.0018

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
