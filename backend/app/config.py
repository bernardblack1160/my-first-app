from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    database_url: str = "postgresql+psycopg://lila:lila@db:5432/lila"
    api_cors_origins: str = "http://localhost:8080,http://localhost:3000"
    session_cookie_name: str = "lila_session"
    session_cookie_secure: bool = False
    session_ttl_days: int = 30
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    @property
    def cors_origins(self) -> list[str]:
        return [origin.strip() for origin in self.api_cors_origins.split(",") if origin.strip()]


settings = Settings()
