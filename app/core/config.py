from pydantic_settings import BaseSettings, SettingsConfigDict
from pathlib import Path


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    APP_ENV: str = "development"
    APP_TITLE: str = "YouTube Slide Extractor"
    APP_VERSION: str = "1.0.0"

    OUTPUT_DIR: Path = Path("./outputs")
    MAX_CONCURRENT_JOBS: int = 3
    JOB_TTL_SECONDS: int = 3600
    LOG_LEVEL: str = "INFO"


settings = Settings()
settings.OUTPUT_DIR.mkdir(parents=True, exist_ok=True)