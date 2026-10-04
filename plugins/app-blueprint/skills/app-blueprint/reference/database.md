# Database

## Local and CI

PostgreSQL runs in `compose.yaml` (`scripts/db.sh up|down|reset|psql`) on a port derived from the app's name
(5432x), so several projects can run side by side. `scripts/db-init.sql` creates the `<pkg>_test` database next to
the app's. CI runs the same image as a service container. Keep one PostgreSQL major in `compose.yaml`, CI and
`infra/main.bicep`. The PostgreSQL 18+ image keeps its data under `/var/lib/postgresql`, not `.../data`.

There is no SQLite fallback. Two databases mean two dialects, `if sqlite:` branches, and tests that pass locally
but not in production.

## Models

SQLAlchemy 2 typed models (`Mapped[...]`, `mapped_column`) in `models.py`. `Base.metadata` has a
**naming_convention**, so constraints have stable names that later migrations can alter and drop. Timestamps are
`DateTime(timezone=True)` with `server_default=func.now()`. The engine uses the psycopg 3 driver
(`Settings.db_url` turns `postgresql://` into `postgresql+psycopg://`) and `pool_pre_ping=True`, because managed
PostgreSQL drops idle connections and a scaled-to-zero app sleeps for hours.

## Migrations (Alembic)

- `scripts/db.sh revision "add x"` upgrades the database first, then autogenerates from `models.py`. **Read every
  generated migration.** Autogenerate writes a rename as drop + add (which loses the data), misses some type
  changes, and doesn't move data. Fix such a migration by hand before applying it.
- Files are named `YYYYMMDD_<slug>_<rev>.py`, so they sort in the order they were written. Ruff fixes and formats
  them as they're written (`post_write_hooks`).
- Never edit a migration that ran anywhere but your machine. Add a new one instead.
- `downgrade()` must work: `tests/test_migrations.py` runs `alembic check` (models and migrations agree) and a full
  downgrade/upgrade round trip.
- The app runs `alembic upgrade head` at startup, inside `pg_advisory_xact_lock`, so replicas starting together
  migrate once. This works because migrations stay backwards compatible with the running version: add a column,
  deploy, then drop the old one in a later release. A destructive change the old version can't survive needs a
  two-step deploy. For long data migrations, use a Container Apps Job instead of startup.
- The settings reach `migrations/env.py` through `Config.attributes["settings"]`, not a URL string, so passwords
  need no `%` escaping and Entra tokens work.

## Tests

The `database` fixture (session-scoped) drops and recreates the schema of the test database, then migrates it
once. The `settings` fixture `TRUNCATE`s every table before each test. Tests go through the HTTP API with
`TestClient`. TRUNCATE is simpler and more robust than rollback-per-test (which breaks when app code opens its own
sessions or threads). Switch to SQLAlchemy's `join_transaction_mode="create_savepoint"` only if the suite gets slow.

## Azure: Entra sign-in, no password

On Azure, PostgreSQL Flexible Server accepts **Entra tokens only** (`passwordAuth: Disabled`), following Microsoft's
recommendation. The app's user-assigned managed identity is an Entra admin of the server (it runs migrations), and
so is the person who deployed it, for `psql`. `DATABASE_ENTRA_AUTH=true` makes `db.py` fetch a token per new
connection (`DefaultAzureCredential`, which picks the managed identity via `AZURE_CLIENT_ID`; azure-identity caches
the token). `DATABASE_URL` holds no password, so it is not a secret.

Connect with `psql` as yourself:
`PGPASSWORD=$(az account get-access-token --resource-type oss-rdbms --query accessToken -o tsv) psql "host=<server>.postgres.database.azure.com user=<you@tenant> dbname=<pkg> sslmode=require"`

Remaining trade-off: the `0.0.0.0` firewall rule lets Azure services of any tenant reach the server, though they
still need an Entra token for it. Private networking (a VNet-integrated Container Apps environment and private
access for the server) closes that. It is worth it for sensitive data, but more infrastructure.
