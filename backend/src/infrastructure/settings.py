from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    database_url: str = "sqlite:///./greenhouse.db"
    allow_sqlite_fallback: bool = True
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


settings = Settings()
