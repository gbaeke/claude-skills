# Quality

## The gate

`scripts/check.sh` runs everything CI runs: ruff (format check, then lint), pyright, pytest (on PostgreSQL), the API
client drift check, Prettier, oxlint, the TypeScript build, Bicep build/lint, and shellcheck (skipped when it isn't
installed; `uvx --from shellcheck-py shellcheck` works without installing). `--fix` first lets ruff and Prettier fix
what they can. CI (`.github/workflows/ci.yml`) is checkout + uv + Node + `scripts/check.sh` with a PostgreSQL
service, so green locally means green in CI.

Before calling a change done, run `scripts/check.sh` and report its result faithfully. If a step was skipped, say
so.

## Seeing the UI without a browser extension

- Screenshots: `chromium --headless=new --screenshot=out.png --window-size=1280,900 --virtual-time-budget=4000 <url>`.
  Add `--force-dark-mode` for dark, `--blink-settings=preferredColorScheme=1` for light.
- Clicks and state (open a panel, check storage across a reload): a short Chrome DevTools Protocol script, e.g. with
  `uv run --with websocket-client`, against `chromium --headless=new --remote-debugging-port=9222`.
- Read every screenshot before calling a UI change done, at desktop and at phone width.
- Stop a server you started by its PID (`$!` when you start it, or `ss -ltnp "sport = :$PORT"`), never with
  `pkill -f <pattern>`: the pattern also matches your own shell's command line, and other people's processes.

## Python

- **ruff** at line length 120, rules `E W F I B UP SIM C4 RET PTH RUF FAST S ARG T20 ERA C90`: the defaults plus
  bugs, modern syntax, simplifications, FastAPI idioms, security (bandit), unused arguments, no `print`, no
  commented-out code, and McCabe complexity ≤ 10 (a function over that gets split). Tests may `assert` and use fake
  secrets.
- **pyright** (standard mode) on `src` and `tests` is the type gate. **ty** (Astral) is faster but still beta (0.0.x);
  revisit it as the gate once it reaches 1.0.
- **pytest** through the HTTP API (`TestClient`, which needs `httpx2`). Use fakes for external services (WorkOS,
  model APIs) behind a `Protocol`, never mocks of the app's own code. Every behaviour change comes with a test in the
  area's file.

## Claude Code in the project

`.claude/settings.json` (committed):
- **ask** before `git commit`, `git push`, `gh pr create|merge`, `git reset --hard` and the Azure deploy/down
  scripts. This enforces "commit and push only when told" mechanically, not only by instruction.
- **PostToolUse hook** `.claude/hooks/format.sh`: after Claude edits a file, ruff fixes and formats `.py`, and
  Prettier formats `frontend/src`. Style never needs a review round.
`CLAUDE.md` holds the commands, layout, git workflow and conventions. Keep it short and current: an outdated
command there costs more than a missing one.

## Dependencies

- **Dependabot** (`.github/dependabot.yml`): weekly, minor and patch grouped per ecosystem (uv, npm, Actions,
  Docker), majors one by one. CI checks each PR. Renovate groups better and maintains lockfiles; switch if Dependabot
  gets noisy.
- **`scripts/versions.sh`**: what is behind right now. That covers direct Python packages (`uv tree --outdated`), npm
  (`npm outdated`), runtimes against endoflife.date (Python, Node LTS, PostgreSQL), GitHub Actions majors, and Bicep
  API versions. Run it when starting work and before adding a dependency.
- Add packages with `uv add` / `npm install` (latest), never by editing a lockfile. Before adding one, check that it is
  maintained (recent releases, open issues answered) and that the standard library or an existing dependency doesn't
  already cover it.

## Simplicity, concretely

- No layer without a second user: no repository class over one query, no service class wrapping one function, no
  config object for a single value.
- When copying code a third time, extract it. The first two times, copying is cheaper than the wrong abstraction.
- A comment says *why*. If a comment explains *what*, rename or split the code instead.
- A setting exists only when two environments need different values.
- Remove a feature flag once the decision is made.
