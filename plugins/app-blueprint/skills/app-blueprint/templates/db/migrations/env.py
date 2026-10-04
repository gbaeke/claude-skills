from alembic import context
from sqlalchemy import text

from {{pkg}}.config import get_settings
from {{pkg}}.db import make_engine
from {{pkg}}.models import Base

MIGRATION_LOCK = 0x6D6967  # any constant: one migration run at a time, however many replicas start together

# the app (run_migrations) and the tests pass their settings; the alembic CLI uses the app's (.env)
settings = context.config.attributes.get("settings") or get_settings()

engine = make_engine(settings)
with engine.connect() as connection:
    context.configure(connection=connection, target_metadata=Base.metadata, compare_server_default=True)
    with context.begin_transaction():
        connection.execute(text("SELECT pg_advisory_xact_lock(:key)"), {"key": MIGRATION_LOCK})
        context.run_migrations()
engine.dispose()
