# Assessment checklist (an existing project)

Check each item, note the evidence (file:line), and rank the gaps by value against effort. Fix them on separate
branches, one topic per branch, only after the user picks them.

**Structure**
- [ ] `src/` layout; `create_app(settings)` factory; settings in one place, every setting documented (and tested).
- [ ] No module over ~400 lines; routers parse input and shape output, and the logic lives in plain modules.
- [ ] One error shape for every failure, including validation errors and 404s; unknown `/api` paths are JSON 404s.
- [ ] Dependencies via `Annotated`; Pydantic models in and out of every route.

**Data**
- [ ] The same database engine and major version locally, in CI and in production (no SQLite stand-in).
- [ ] Migrations: naming convention on the metadata, sortable file names, an `alembic check` test, working downgrades,
      a lock if they run at startup.
- [ ] Tests hit a real database, and each test starts from empty tables.

**Frontend**
- [ ] API types generated from OpenAPI (not hand-written), with a drift check.
- [ ] Server state in TanStack Query (no `useEffect` fetching); design tokens instead of raw colours.
- [ ] Current packages (`react-router`, not `react-router-dom`); no `--legacy-peer-deps` workarounds without a
      written reason.

**Quality**
- [ ] One `check.sh` that CI runs: formatter, linter (more than default rules), type checker (Python and TS), tests.
- [ ] CI exists and runs on PRs; Dependabot or Renovate is on.
- [ ] `CLAUDE.md` is short and correct; `.claude/settings.json` asks before commit/push and formats on edit.
- [ ] Request ids in logs and responses; JSON logs when deployed; security headers.

**Azure**
- [ ] Infra and app deploy separately; app config lives in code, not portal edits.
- [ ] Database with Entra / managed identity instead of a password; secrets never in outputs or logs.
- [ ] Bicep API versions under two years old (linter rule on).
- [ ] Single-replica assumptions written down where they live (in-memory state, startup work).

**Security**
- [ ] Secrets only in `.env` (ignored) and platform secrets; `.env.example` has placeholders.
- [ ] Session cookies httponly + secure + SameSite; no state-changing GETs; redirects limited to own paths.
