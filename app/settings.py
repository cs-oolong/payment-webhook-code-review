from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env")

    DATABASE_URL: str = "sqlite+aiosqlite:///:memory:"
    KAFKA_BOOTSTRAP_SERVERS: str = "localhost:9092"
    PAYMENT_WEBHOOK_SECRET: str = "local-development-secret"


settings = Settings()
