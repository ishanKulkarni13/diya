"""
Central settings for the 2ndEye API.

All configuration is loaded from environment variables (or a .env file).
The app will refuse to start if any required variable is missing — this is intentional.
Never add default values for secrets or credentials.
"""

from pydantic import Field, PostgresDsn, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class AppSettings(BaseSettings):
    """General application settings."""

    app_name: str = "2ndEye API"
    environment: str = Field(default="development")  # development | staging | production
    debug: bool = Field(default=False)
    api_v1_prefix: str = "/api/v1"

    @field_validator("environment")
    @classmethod
    def validate_environment(cls, v: str) -> str:
        allowed = {"development", "staging", "production"}
        if v not in allowed:
            raise ValueError(f"environment must be one of {allowed}, got '{v}'")
        return v

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


class AuthSettings(BaseSettings):
    """JWT and session auth settings."""

    secret_key: str = Field(..., description="HS256 signing key — required, no default")
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 30
    refresh_token_expire_days: int = 30

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


class DatabaseSettings(BaseSettings):
    """PostgreSQL async connection settings."""

    db_host: str = Field(default="localhost")
    db_port: int = Field(default=5432)
    db_user: str = Field(default="admin")
    db_password: str = Field(..., description="Postgres password — required, no default")
    db_name: str = Field(default="secondeye_dev")

    @property
    def async_url(self) -> str:
        """Async SQLAlchemy connection URL using asyncpg driver."""
        return (
            f"postgresql+asyncpg://{self.db_user}:{self.db_password}"
            f"@{self.db_host}:{self.db_port}/{self.db_name}"
        )

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


class ObservabilitySettings(BaseSettings):
    """Logging and tracing settings."""

    # "pretty" for dev (human-readable), "json" for staging/production
    log_format: str = Field(default="pretty")
    log_level: str = Field(default="INFO")

    @field_validator("log_format")
    @classmethod
    def validate_log_format(cls, v: str) -> str:
        allowed = {"pretty", "json"}
        if v not in allowed:
            raise ValueError(f"log_format must be one of {allowed}, got '{v}'")
        return v

    @field_validator("log_level")
    @classmethod
    def validate_log_level(cls, v: str) -> str:
        allowed = {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}
        if v.upper() not in allowed:
            raise ValueError(f"log_level must be one of {allowed}, got '{v}'")
        return v.upper()

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


class ProviderSettings(BaseSettings):
    """External provider credentials — all optional until the module is active."""

    gemini_api_key: str | None = Field(default=None, description="Google AI Studio API key for Gemini")
    gemini_model_name: str = Field(default="gemini-2.5-flash", description="Gemini model to use for Assist")
    fcm_credentials_path: str | None = Field(default=None, description="Path to Firebase service account JSON")

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


class GuardianSettings(BaseSettings):
    """Guardian relationship settings."""

    invite_expiry_days: int = Field(default=7, description="Days until guardian invite expires")

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


class Settings:
    """
    Aggregated settings object.

    Import and use `settings` from this module everywhere in the app.
    Never instantiate individual setting groups directly outside this file.
    """

    def __init__(self) -> None:
        self.app = AppSettings()
        self.auth = AuthSettings()
        self.db = DatabaseSettings()
        self.observability = ObservabilitySettings()
        self.providers = ProviderSettings()
        self.guardian = GuardianSettings()


settings = Settings()
