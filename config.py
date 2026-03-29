from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    # ── Telegram ──────────────────────────────────────────────────────────────
    TELEGRAM_BOT_TOKEN: str
    TELEGRAM_WEBHOOK_SECRET: str
    WEBHOOK_BASE_URL: str = ""   # set after first deploy when Railway URL is known

    # ── LLM provider ──────────────────────────────────────────────────────────
    # Set to "anthropic" (default) or "openai"
    LLM_PROVIDER: str = "anthropic"

    # Anthropic — primary provider
    ANTHROPIC_API_KEY: str = ""
    ANTHROPIC_MODEL: str = "claude-3-5-sonnet-20241022"

    # OpenAI — optional, kept for future use
    OPENAI_API_KEY: str = ""
    OPENAI_MODEL: str = "gpt-4o"

    # ── Database ──────────────────────────────────────────────────────────────
    DATABASE_URL: str = "sqlite+aiosqlite:///./event_planner.db"

    # ── Storage ───────────────────────────────────────────────────────────────
    FILES_STORAGE_PATH: str = "./data/files"

    # ── Logging ───────────────────────────────────────────────────────────────
    LOG_LEVEL: str = "INFO"


settings = Settings()
