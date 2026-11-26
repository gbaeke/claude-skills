-- Runs once, when the PostgreSQL volume is created.
-- One database per agent (and one for the BFF) on the same server, so agents never
-- share tables and each can have its own retention and upgrades.
-- On an existing volume, create a new agent's database by hand:
--   docker compose exec postgres psql -U postgres -c "CREATE DATABASE <name>"
CREATE DATABASE {{agent_db}};
-- {{#web}}
CREATE DATABASE bff;
-- {{/web}}
-- scaffold.py add-agent adds new databases above this line
