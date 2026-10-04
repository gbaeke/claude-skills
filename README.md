# claude-skills

My Claude Code skills, packaged as plugins in one marketplace (`geba-skills`). Install only what you need.

## Install

```
/plugin marketplace add gbaeke/claude-skills
/plugin install drawio-diagram@geba-skills
```

From a terminal: `claude plugin marketplace add gbaeke/claude-skills`, then
`claude plugin install drawio-diagram@geba-skills`.

Update after a push: `claude plugin update drawio-diagram@geba-skills` (or turn on auto-update for this
marketplace in `/plugin` → Marketplaces).

## Plugins

| Plugin | What it does |
|---|---|
| `drawio-diagram` | Light-themed draw.io diagrams in a house style: architecture, pipelines, Azure resource groups with Azure icons. Generated from Python, verified by rendering to PNG. |
| `app-blueprint` | New full-stack apps (or a module added to an existing one): FastAPI, React/Vite, PostgreSQL + Alembic, optional WorkOS, Azure Container Apps. Renders a project that passes its own `scripts/check.sh` on day one, with the latest package versions. |

## Add a skill

1. `plugins/<name>/.claude-plugin/plugin.json` with at least `{"name": "<name>", "description": "…"}`.
2. The skill in `plugins/<name>/skills/<name>/SKILL.md` (plus its scripts). Reference files relative to the skill's
   own directory, never `~/.claude/skills/…`: installed plugins live under `~/.claude/plugins/`.
3. An entry in `.claude-plugin/marketplace.json` with `"source": "./plugins/<name>"`.
4. `claude plugin validate .` and `claude plugin validate plugins/<name>`, then commit and push.
