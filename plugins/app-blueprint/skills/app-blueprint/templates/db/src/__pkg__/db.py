from collections.abc import Iterator
from pathlib import Path
from typing import Annotated

from fastapi import Depends, Request
from sqlalchemy import Engine, create_engine
{{#azure}}
from sqlalchemy import event
{{/azure}}
from sqlalchemy.orm import Session

from .config import Settings

ROOT = Path(__file__).resolve().parents[2]  # where alembic.ini and migrations/ are
{{#azure}}
ENTRA_SCOPE = "https://ossrdbms-aad.database.windows.net/.default"
{{/azure}}


def make_engine(settings: Settings) -> Engine:
    # managed PostgreSQL drops idle connections (and a scaled-to-zero app sleeps for hours): test each before use
    engine = create_engine(settings.db_url, pool_pre_ping=True)
{{#azure}}
    if settings.database_entra_auth:
        _use_entra_tokens(engine)
{{/azure}}
    return engine
{{#azure}}


def _use_entra_tokens(engine: Engine) -> None:
    """Azure: sign in to PostgreSQL with the app's managed identity (or your az login, locally) instead of a
    password. Each new connection gets a fresh token; azure-identity caches it until shortly before it expires."""
    from azure.identity import DefaultAzureCredential

    credential = DefaultAzureCredential()

    @event.listens_for(engine, "do_connect")
    def _token(_dialect, _conn_rec, _cargs, cparams) -> None:
        cparams["password"] = credential.get_token(ENTRA_SCOPE).token
{{/azure}}


def run_migrations(settings: Settings) -> None:
    """Upgrade the database to the latest migration. The app does this at startup, under a lock (migrations/env.py)."""
    from alembic import command
    from alembic.config import Config

    cfg = Config(str(ROOT / "alembic.ini"))
    cfg.attributes["settings"] = settings
    command.upgrade(cfg, "head")


def get_session(request: Request) -> Iterator[Session]:
    with request.app.state.session_factory() as session:
        yield session


SessionDep = Annotated[Session, Depends(get_session)]
