# PostgreSQL and PgBouncer

## One server, one database per agent

`postgres/init.sql` creates one database per agent plus `bff` on the first start of the volume. Each agent's
database holds only its own tables: LangGraph's `checkpoints`, `checkpoint_blobs`, `checkpoint_writes`,
`checkpoint_migrations` (created by `checkpointer.setup()`) and `a2a_tasks` (created by the task store). Agents
never read each other's conversations, and `checkpoint_migrations` can't fight across LangGraph versions. Only
`DATABASE_URL` differs. Prefer a database per agent over a schema per agent: no code change and real isolation.

A new database on an existing volume: `docker compose exec postgres psql -U postgres -c "CREATE DATABASE <db>"`.

## PgBouncer

Services connect to `pgbouncer:6432`, never to PostgreSQL directly (`edoburu/pgbouncer`, the same port as the
built-in PgBouncer of Azure Database for PostgreSQL Flexible Server).

- `POOL_MODE=transaction`: a real connection is lent for one transaction, then returned.
- `DEFAULT_POOL_SIZE=10`: **at most** 10 real connections per database, opened only when busy; extra transactions
  queue briefly. Each database has its own pool.
- `MAX_PREPARED_STATEMENTS=200`: the task store's driver (asyncpg) uses prepared statements, which transaction
  mode otherwise breaks. The checkpointer already turns them off (`prepare_threshold=0`).
- Watch it: `docker compose exec -e PGPASSWORD=postgres postgres psql -h pgbouncer -p 6432 -U postgres -d pgbouncer
  -c "SHOW POOLS"` (`cl_active`, `cl_waiting`, `sv_active`, `sv_idle`).

Measured: each agent replica holds about 6 client connections (1 checkpointer + ~5 task-store pool); five
helpdesk replicas under 40 parallel conversations held 29 client connections that shared 10 real ones, no client
waiting, 2.2 ms per transaction. Without PgBouncer, PostgreSQL's default 100 connections run out at ~15 replicas.

## Still to do in production

- A **retention job**: open-source savers never delete checkpoints; delete threads older than the retention period
  (`checkpointer.adelete_thread`) and their `a2a_tasks` rows.
- A **connection pool for the checkpointer** (`AsyncConnectionPool` from `psycopg_pool`) once one replica writes
  many checkpoints at once; `from_conn_string` uses a single connection.
- Managed PostgreSQL with Entra authentication, backups and TLS; per-agent database users.
