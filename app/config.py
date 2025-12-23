from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # Required (no default) -> must come from env/.env
    DATABASE_URL: str

    # Optional defaults
    TCP_HOST: str = "0.0.0.0"
    TCP_PORT: int = 12345
    API_HOST: str = "0.0.0.0"
    API_PORT: int = 8000

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,  # allow database_url or DATABASE_URL in env
    )


settings = Settings()
