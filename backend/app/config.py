from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    app_name: str = "CodeVerse API"
    app_env: str = "development"
    database_url: str = "sqlite:///./codeverse.db"
    jwt_secret_key: str = "development-only-change-me"
    jwt_expire_minutes: int = 60

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

settings = Settings()

if settings.app_env.lower() == "production" and settings.jwt_secret_key == "development-only-change-me":
    raise RuntimeError("JWT_SECRET_KEY must be set to a strong random value in production.")
