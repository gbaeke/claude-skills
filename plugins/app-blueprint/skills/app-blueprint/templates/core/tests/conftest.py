{{#db}}
import os

{{/db}}
import pytest
from fastapi.testclient import TestClient
{{#db}}
from sqlalchemy import create_engine, text
from sqlalchemy.exc import OperationalError
{{/db}}

from {{pkg}}.api.app import create_app
from {{pkg}}.config import Settings, settings_without_env_file
{{#db}}
from {{pkg}}.db import run_migrations
from {{pkg}}.models import Base

# the same PostgreSQL as the app (scripts/db.sh up), its own database; CI sets TEST_DATABASE_URL
TEST_DATABASE_URL = os.environ.get(
    "TEST_DATABASE_URL", "postgresql://{{pkg}}:{{pkg}}@localhost:{{pg_port}}/{{pkg}}_test"
)
{{/db}}


@pytest.fixture(autouse=True)
def isolate_from_env(monkeypatch):
    """No setting leaks in from the shell: tests build their Settings explicitly."""
    for name in Settings.model_fields:
        monkeypatch.delenv(name.upper(), raising=False)
{{#db}}


@pytest.fixture(scope="session")
def database() -> str:
    """A fresh schema at the start of the run, migrated to head once."""
    settings = settings_without_env_file(database_url=TEST_DATABASE_URL)
    engine = create_engine(settings.db_url)
    try:
        with engine.begin() as c:
            c.execute(text("DROP SCHEMA public CASCADE"))
            c.execute(text("CREATE SCHEMA public"))
    except OperationalError as e:
        pytest.exit(f"No test database at {TEST_DATABASE_URL}: start it with scripts/db.sh up\n{e}", 2)
    finally:
        engine.dispose()
    run_migrations(settings)
    return TEST_DATABASE_URL
{{/db}}


{{#db}}
@pytest.fixture
def settings(database) -> Settings:
    """Empty tables for every test (truncating is much faster than migrating again)."""
    settings = settings_without_env_file(database_url=database)
    engine = create_engine(settings.db_url)
    with engine.begin() as c:
        tables = ", ".join(t.name for t in Base.metadata.sorted_tables)
        c.execute(text(f"TRUNCATE {tables} RESTART IDENTITY CASCADE"))
    engine.dispose()
    return settings
{{/db}}
{{^db}}
@pytest.fixture
def settings() -> Settings:
    return settings_without_env_file()
{{/db}}


@pytest.fixture
def client(settings):
    """The app on test settings; `with` runs its startup and shutdown."""
    with TestClient(create_app(settings)) as c:
        yield c
