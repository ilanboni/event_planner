from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    TELEGRAM_BOT_TOKEN: str
    TELEGRAM_WEBHOOK_SECRET: str
    WEBHOOK_BASE_URL: str

    OPENAI_API_KEY: str = ""
    OPENAI_MODEL: str = "gpt-4o"

    DATABASE_URL: str = "sqlite+aiosqlite:///./event_planner.db"
    FILES_STORAGE_PATH: str = "./data/files"
    LOG_LEVEL: str = "INFO"


settings = Settings()
