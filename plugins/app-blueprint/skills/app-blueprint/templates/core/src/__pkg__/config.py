from functools import lru_cache
from typing import Any

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Every setting the app reads, from the environment or .env. .env.example lists them all (a test checks)."""

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    host: str = "127.0.0.1"
    port: int = 8000
    log_json: bool = False  # JSON log lines (the deploy sets it)
{{#db}}
    database_url: str = "postgresql://{{pkg}}:{{pkg}}@localhost:{{pg_port}}/{{pkg}}"
{{#azure}}
    database_entra_auth: bool = False  # Azure: a managed identity token instead of a password (the deploy sets it)
{{/azure}}
{{/db}}
{{#auth}}
    workos_client_id: str = ""  # empty: no sign-in
    workos_api_key: str = ""
    session_secret: str = ""  # encrypts the session cookie
    allowed_users: str = ""  # comma separated; empty: everyone WorkOS lets in
    public_url: str = ""  # the address people use, when a proxy hides it (Azure Container Apps)

    @property
    def auth_enabled(self) -> bool:
        return bool(self.workos_client_id)

    def user_allowed(self, email: str) -> bool:
        allowed = {e.strip().lower() for e in self.allowed_users.split(",") if e.strip()}
        return not allowed or email.lower() in allowed
{{/auth}}
{{#db}}

    @property
    def db_url(self) -> str:
        """DATABASE_URL with the psycopg 3 driver, whatever scheme it was given in (Azure hands out postgresql://)."""
        scheme, _, rest = self.database_url.partition("://")
        return f"postgresql+psycopg://{rest}" if scheme in ("postgres", "postgresql") else self.database_url
{{/db}}


@lru_cache
def get_settings() -> Settings:
    return Settings()


def settings_without_env_file(**values: Any) -> Settings:
    """Settings from these values and the environment only: .env is not read (tests, tools)."""
    return Settings(_env_file=None, **values)  # pyright: ignore[reportCallIssue]  (pydantic-settings' init option)
