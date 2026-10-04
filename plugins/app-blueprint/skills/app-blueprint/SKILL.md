---
name: app-blueprint
description: Start, extend or tidy up a full-stack web app the house way - Python FastAPI backend (uv, ruff, pyright, pytest), React + Vite + TypeScript + Tailwind + TanStack Query SPA served by the backend, PostgreSQL in a local container with SQLAlchemy and Alembic migrations, optional WorkOS AuthKit sign-in, Azure Container Apps with Bicep and azure-up / azure-deploy / azure-down scripts, one quality gate (scripts/check.sh) that CI runs too. Scaffolds a working project from modules (frontend, db, auth, azure), adds a module to an existing repo, or aligns an existing repo with the same practices. Use when the user wants a new app, project, service, API or web app; to add a database, migrations, sign-in/auth/WorkOS, Azure deployment or CI to an app; or asks how their app should be structured, kept simple, or kept up to date.
---

# App blueprint

A starting point that runs and passes its own quality gate on day one, plus the principles to keep it that way.
`scripts/scaffold.py` renders a project from `templates/` with only the modules asked for, and installs the
**latest** releases of every package. Templates never pin versions. `reference/` explains each part and its
trade-offs. Read the relevant reference file before changing that part of a project.

| Module | What | Default |
|---|---|---|
| core | FastAPI under `src/<pkg>/`, settings, error envelope, request ids, JSON logs, security headers, pytest, ruff + pyright, `scripts/check.sh`, `scripts/versions.sh`, CI, Dependabot, Dockerfile, `CLAUDE.md` with the git rules, `.claude/settings.json` | always |
| frontend | React + Vite SPA in `frontend/`, served by FastAPI. The API client and TanStack Query helpers are generated from OpenAPI (hey-api). Tailwind v4 tokens, light and dark | on |
| db | PostgreSQL in Docker Compose (`scripts/db.sh`), SQLAlchemy 2, Alembic, tests on a real PostgreSQL | on |
| auth | WorkOS AuthKit sign-in (sealed sessions), off until `WORKOS_CLIENT_ID` is set | **off**: only when asked |
| azure | Bicep: `infra/main.bicep` (shared infra) and `infra/app.bicep` (the app only), plus `azure-up` / `azure-deploy` / `azure-down` | on |

## Principles (apply to every change, scaffolded or not)

1. **Simple first.** Write the smallest thing that works. Don't abstract until something repeats a third time.
   Don't put service/repository/factory layers over FastAPI and SQLAlchemy until a module needs one. No options
   nobody asked for.
2. **One source of truth.** Settings live in `config.py`, mirrored in `.env.example`, and a test checks they match.
   The database schema lives in `models.py` and reaches the database only through migrations. API types come from
   the Pydantic models via OpenAPI and are never written twice. Design tokens live in `index.css`.
3. **Parity.** Use the same PostgreSQL major locally, in CI and on Azure. Tests run against a real PostgreSQL, never
   SQLite. Deploy the same image you can run with `docker compose --profile app up`.
4. **One gate.** `scripts/check.sh` is what CI runs. A change is done when it passes; a skipped step is reported as
   skipped.
5. **Current versions.** Start on the latest releases and keep them current deliberately (see "Freshness").
6. **Delete freely.** Remove dead code, and remove what a change makes unused. Don't leave commented-out code.
7. **Grow by splitting.** Once a module passes ~400 lines or a router holds business logic, split it. Move logic into
   a plain module next to the router. Once the app has more than ~5 areas, move to per-domain packages
   (`src/<pkg>/<area>/{router,models,service}.py`). See `reference/backend.md`.

## Git (always)

- Work on a branch. Before the first change of a task, run `git switch -c <short-topic>`; never work on `main`.
- **Commit and push only when the user says so.** That includes the scaffold's first commit. Open or merge a PR only
  when asked. The generated `.claude/settings.json` makes Claude Code ask before `git commit` / `git push` /
  `gh pr` / Azure deploys.
- Commit message: `Area: what changed` (imperative, under 72 characters), then a body that says *why*. One logical
  change per commit. PRs are squash-merged.

## A. New project

1. **Ask** (AskUserQuestion, one round): the name (kebab-case), what the app is for in one sentence, and the modules,
   with the defaults above. Ask about auth explicitly; it stays off unless they want it.
2. **Prerequisites.** Check them, and offer install commands without running system installs unasked: `uv`; Node 24+
   with frontend; Docker with db; `az` (and `az login` for deploys) with azure. With **auth**, also the WorkOS CLI:
   `command -v workos` (install with `npm install -g workos`), then `workos auth status --mode agent`. If it isn't
   authenticated, have the user run `! workos auth login`. The CLI manages redirect/sign-out URIs, users and
   environments, so no dashboard clicking is needed. See `reference/auth-workos.md`.
3. **Scaffold** into the target folder:
   `python3 <this skill>/scripts/scaffold.py <dest> --name <name> [--with auth] [--without frontend,db,azure]`.
   It renders the files, runs `git init`, `uv add`s / `npm install`s the latest versions, generates the API client and
   formats everything.
4. **Verify:** `scripts/db.sh up` (db), then `scripts/check.sh` must pass, then `scripts/versions.sh`. Report what is
   behind. A new scaffold should only show the holds listed under "Freshness".
5. **Make it theirs:** write the one-paragraph description at the top of `CLAUDE.md` and `README.md`. Replace the
   `notes` example with the app's first real resource, keeping its shape: model → migration
   (`scripts/db.sh revision`) → router → test → page. Then delete what's left of `notes`.
6. **Auth chosen:** create or choose the WorkOS environment, put `WORKOS_CLIENT_ID`, `WORKOS_API_KEY` and
   `SESSION_SECRET` (`openssl rand -base64 32`) into `.env` (never into the chat), and run
   `scripts/workos-uris.sh add http://localhost:8000` (and `:5173` for Vite).
7. Suggest the first commit. Make it only after the user says yes.

## B. Add a module to an existing project

The scaffold never overwrites. Render a **reference** project with the same name and modules, plus the new module,
into the scratchpad with `--no-install`, then `diff -r` it against the repo. Port the new module's files and its
blocks in shared files (`config.py`, `.env.example`, `app.py`, `check.sh`, CI, `CLAUDE.md`) by hand, adapting to
what the repo already does. Add the module's packages with `uv add` / `npm install` (the lists are at the top of
`scripts/scaffold.py`). Then run `scripts/check.sh`.

## C. An existing project that wasn't scaffolded

Don't rewrite it. Read `reference/checklist.md`, assess the repo against it, and present the gaps ranked by value
and effort. Then fix what the user picks, one branch per topic. The reference project from B is the model to copy
from.

## Freshness

- At the start of work on a project, and before adding any dependency, run `scripts/versions.sh`, or check the
  latest release with `npm view <pkg> version` / `uv pip index versions <pkg>` / the project's releases page. Never
  add a dependency from memory: confirm it is maintained and current.
- Minor and patch updates go in together, followed by `scripts/check.sh`. Each major update goes on its own branch,
  after reading its changelog or migration guide.
- Current **holds**, each with a reason. Re-check every hold whenever versions come up, and drop it once the reason
  is gone:
  - **TypeScript 6, not 7.** TS 7 (the native port) has no JavaScript compiler API yet. `@hey-api/openapi-ts` (and
    `openapi-typescript`) crash on it. Re-test with `npm i -D typescript@latest && npm run gen:api`.
  - **Node 24 in the Dockerfile and CI** until Node 26 becomes LTS (2026-10-28).
- Keep the PostgreSQL major the same in `compose.yaml`, CI and `infra/main.bicep`.

## Reference

- `reference/backend.md`: layout, how it grows, routes, errors, settings, logging, middleware
- `reference/database.md`: local PostgreSQL, models, migrations, tests, Entra auth on Azure
- `reference/frontend.md`: why a SPA, the generated client, data fetching, styling, linting, tests
- `reference/auth-workos.md`: sealed sessions, the WorkOS CLI, setup, what it does and doesn't protect
- `reference/azure.md`: the infra/app split, the scripts, identity, what's left out and how to add it
- `reference/quality.md`: the gate, lint and type rules, hooks and permissions, CI, Dependabot
- `reference/checklist.md`: the assessment list for workflow C
