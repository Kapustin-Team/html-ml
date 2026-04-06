from pathlib import Path
from typing import Optional
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file='.env', env_file_encoding='utf-8', extra='ignore')

    app_env: str = 'development'
    database_url: str = 'sqlite:///data/html_ml.db'
    bankroll_usd: float = 3000.0
    flat_bet_usd: float = 100.0
    polymarket_base_url: str = 'https://gamma-api.polymarket.com'
    hltv_live_url: str = 'https://www.hltv.org/matches'
    collector_poll_seconds: float = 5.0
    browser_headless: bool = False
    data_dir: Path = Field(default=Path('data'))
    openrouter_api_key: Optional[str] = None
    openrouter_base_url: str = 'https://openrouter.ai/api/v1'
    openrouter_model: str = 'openai/gpt-4.1-mini'


settings = Settings()
