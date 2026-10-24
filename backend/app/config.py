from pathlib import Path
from urllib.parse import urlsplit

from pydantic import field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict
from sqlalchemy.engine import make_url

ROOT = Path(__file__).resolve().parents[1]
PROJECT_ROOT = ROOT.parent


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=(PROJECT_ROOT / ".env", ROOT / ".env"),
        env_file_encoding="utf-8", extra="ignore", hide_input_in_errors=True,
    )
    app_env: str = "development"
    app_timezone: str = "Asia/Karachi"
    database_url: str = f"sqlite:///{(PROJECT_ROOT / '.local' / 'northstar.db').as_posix()}"
    session_hours: int = 12
    secure_cookies: bool = False
    allowed_origins: str = "http://127.0.0.1:5173,http://localhost:5173,http://127.0.0.1:8000,http://localhost:8000"
    trusted_hosts: str = "localhost,127.0.0.1,testserver"
    llm_mode: str = "offline"
    openrouter_api_key: str = ""
    openrouter_model: str = "google/gemma-4-31b-it:free"
    openrouter_base_url: str = "https://openrouter.ai/api/v1"
    openrouter_timeout_seconds: int = 30
    openrouter_max_output_tokens: int = 512
    return_window_days: int = 30
    confirmation_minutes: int = 10
    embedding_model: str = "sentence-transformers/all-MiniLM-L6-v2"
    embedding_mode: str = "local"
    seed_demo: bool = True

    @field_validator("app_env")
    @classmethod
    def valid_environment(cls, value):
        if value not in {"development", "test", "production"}:
            raise ValueError("APP_ENV must be development, test, or production")
        return value

    @model_validator(mode="after")
    def production_safety(self):
        if not self.hosts or any("/" in host or ":" in host for host in self.hosts):
            raise ValueError("TRUSTED_HOSTS must contain hostnames without scheme, path, or port")
        if self.app_env != "production":
            return self
        if not self.secure_cookies:
            raise ValueError("Production requires SECURE_COOKIES=true")
        if self.seed_demo:
            raise ValueError("Production requires SEED_DEMO=false; provision accounts with app.manage_users")
        if not self.origins:
            raise ValueError("Production requires explicit ALLOWED_ORIGINS")
        for origin in self.origins:
            parsed = urlsplit(origin)
            if (parsed.scheme != "https" or not parsed.hostname or "*" in origin
                    or parsed.path or parsed.query or parsed.fragment or parsed.username
                    or parsed.hostname in {"localhost", "127.0.0.1", "testserver"}):
                raise ValueError("Production ALLOWED_ORIGINS must be exact public HTTPS origins without trailing slashes")
        if any("*" in host or host == "testserver" for host in self.hosts):
            raise ValueError("Production TRUSTED_HOSTS must be exact hostnames without wildcards or testserver")
        if not any(host not in {"localhost", "127.0.0.1"} for host in self.hosts):
            raise ValueError("Production TRUSTED_HOSTS must include the public backend hostname")
        try:
            url = make_url(self.database_url)
        except Exception:
            raise ValueError("DATABASE_URL is not a valid SQLAlchemy database URL") from None
        if url.drivername != "postgresql+psycopg":
            raise ValueError("Production requires a postgresql+psycopg DATABASE_URL")
        if url.query.get("sslmode") not in {"require", "verify-ca", "verify-full"}:
            raise ValueError("Production DATABASE_URL must explicitly require TLS; prefer sslmode=verify-full")
        return self

    @field_validator("database_url", mode="before")
    @classmethod
    def blank_database_uses_local_default(cls, value):
        return value or f"sqlite:///{(PROJECT_ROOT / '.local' / 'northstar.db').as_posix()}"

    @field_validator("llm_mode")
    @classmethod
    def valid_mode(cls, value):
        if value not in {"offline", "openrouter"}:
            raise ValueError("LLM_MODE must be offline or openrouter")
        return value

    @property
    def origins(self):
        return [value.strip() for value in self.allowed_origins.split(",") if value.strip()]

    @property
    def hosts(self):
        return [value.strip() for value in self.trusted_hosts.split(",") if value.strip()]


settings = Settings()
