#!/usr/bin/env python3
"""Scaffold a Deep Agents + A2A project, or add another agent to one.

    scaffold.py new DEST --name my-app [--agent helpdesk] [--agent-title "Helpdesk agent"]
                         [--agent-description "..."] [--without mcp,web] [--latest]
                         [--model openai:azure-gpt-6-luna] [--model-base-url http://host.docker.internal:4000/v1]
    scaffold.py add-agent DEST --agent hr [--agent-title "HR agent"] [--agent-description "..."] [--mcp]

Modules (each a folder in ../templates, plus {{#module}} ... {{/module}} blocks in shared files):
  core  always: the agent service (A2A wrapper + deep agent, one config folder per agent), PostgreSQL with one
        database per agent, PgBouncer, a CLI with chat / smoke / stress tools, compose.yaml, Dockerfile, README
  mcp   a stateless FastMCP server with a sample tool (save_note) that needs human approval        (default on)
  web   a BFF (FastAPI) and a web UI: chats, streaming, progress, approval cards, Markdown         (default on)

Versions: by default the project gets the versions last verified end to end (pins in each pyproject.toml plus the
uv.lock files, see ../reference/versions.md). --latest drops the pins and resolves the newest releases with
`uv lock` instead; run the smoke test afterwards, because these libraries change quickly.

Template syntax, in file contents and paths:
  {{app}} {{title}} {{agent}} {{agent_db}} {{agent_title}} {{agent_description}} {{model}} {{model_base_url}}
  {{port}} (the web UI's host port, stable per app so several projects run side by side).
  __agent__ in a path becomes the agent name. A line holding {{#m}} / {{/m}} opens / closes a block kept only with
  module m; {{^m}} / {{/m}} a block kept only without it. Marker lines are dropped. A block opened and closed on
  one line keeps or drops just that phrase.
"""

import argparse
import re
import shutil
import subprocess
import sys
import zlib
from pathlib import Path

TEMPLATES = Path(__file__).resolve().parent.parent / "templates"
MODULES = ("mcp", "web")
SERVICES = {"core": ["agent", "cli"], "mcp": ["mcp-server"], "web": ["bff"]}  # folders with a pyproject.toml
COMPOSE_MARK = "  # --- scaffold.py add-agent inserts new agents above this line ---"
SQL_MARK = "-- scaffold.py add-agent adds new databases above this line"

MARKER = re.compile(r"\{\{([#^/])(\w+)\}\}")
INLINE = re.compile(r"\{\{([#^])(\w+)\}\}(.*?)\{\{/\2\}\}")
OWN_LINE = r"\s*(#|//|--|<!--)?\s*{}\s*(-->)?\s*"


def render(text: str, enabled: set[str], names: dict[str, str]) -> str:
    text = INLINE.sub(lambda m: m[3] if (m[2] in enabled) == (m[1] == "#") else "", text)
    out, stack = [], []
    for line in text.splitlines(keepends=True):
        m = MARKER.search(line)
        if m:
            if not re.fullmatch(OWN_LINE.format(re.escape(m[0])), line):
                sys.exit(f"a block marker must have its own line (or open and close on one line): {line!r}")
            kind, mod = m.groups()
            if mod not in MODULES:
                sys.exit(f"unknown module {mod!r} in a template marker")
            if kind == "/":
                stack.pop()
            else:
                stack.append((mod, kind == "#"))
            continue
        if all((mod in enabled) == want for mod, want in stack):
            out.append(line)
    if stack:
        sys.exit(f"unclosed template block: {stack}")
    text = "".join(out)
    for key, value in names.items():
        text = text.replace("{{" + key + "}}", value)
    return text


def copy_tree(src: Path, dest: Path, enabled: set[str], names: dict[str, str]) -> None:
    for path in sorted(src.rglob("*")):
        if path.is_dir() or "__pycache__" in path.parts:
            continue
        target = dest / str(path.relative_to(src)).replace("__agent__", names["agent"])
        target.parent.mkdir(parents=True, exist_ok=True)
        if path.name == "uv.lock":  # lock files are data, never templated
            shutil.copyfile(path, target)
        else:
            target.write_text(render(path.read_text(), enabled, names))
        target.chmod(path.stat().st_mode)


def run(cmd: list[str], cwd: Path) -> None:
    print("+", " ".join(cmd), flush=True)
    if subprocess.run(cmd, cwd=cwd).returncode:
        sys.exit(f"failed: {' '.join(cmd)} (in {cwd})")


def use_latest(dest: Path, enabled: set[str]) -> None:
    """Drop the verified pins and resolve the newest releases."""
    for module, folders in SERVICES.items():
        if module != "core" and module not in enabled:
            continue
        for folder in folders:
            pyproject = dest / folder / "pyproject.toml"
            pyproject.write_text(re.sub(r'("[\w\[\],.-]+)==[\w.]+"', r'\1"', pyproject.read_text()))
            (dest / folder / "uv.lock").unlink(missing_ok=True)
            run(["uv", "lock", "--quiet", "--upgrade"], dest / folder)


def agent_names(agent: str, title: str | None, description: str | None) -> dict[str, str]:
    if not re.fullmatch(r"[a-z][a-z0-9]*(-[a-z0-9]+)*", agent):
        sys.exit("--agent must be kebab-case: lowercase letters, digits and dashes")
    return {
        "agent": agent,
        "agent_db": agent.replace("-", "_"),
        "agent_title": title or f"{agent.replace('-', ' ').capitalize()} agent",
        "agent_description": description or "Answers questions for the team.",
    }


def cmd_new(args) -> None:
    if not re.fullmatch(r"[a-z][a-z0-9]*(-[a-z0-9]+)*", args.name):
        sys.exit("--name must be kebab-case")
    without = {m for m in args.without.split(",") if m}
    if unknown := without - set(MODULES):
        sys.exit(f"unknown modules: {', '.join(sorted(unknown))} (known: {', '.join(MODULES)})")
    enabled = set(MODULES) - without
    if args.dest.exists() and any(args.dest.iterdir()):
        sys.exit(f"{args.dest} exists and is not empty")
    names = {
        "app": args.name,
        "title": args.title or args.name.replace("-", " ").title(),
        "model": args.model,
        "model_base_url": args.model_base_url,
        "port": str(8100 + zlib.crc32(f"{args.name}:http".encode()) % 800),
        **agent_names(args.agent, args.agent_title, args.agent_description),
    }
    args.dest.mkdir(parents=True, exist_ok=True)
    for module in ("core", *MODULES):
        if module == "core" or module in enabled:
            copy_tree(TEMPLATES / module, args.dest, enabled, names)
    if args.latest:
        use_latest(args.dest, enabled)
    print(f"Rendered {names['app']} in {args.dest} with agent '{names['agent']}' and: "
          f"{', '.join(m for m in MODULES if m in enabled) or 'core only'}"
          f" ({'newest' if args.latest else 'verified'} versions)")
    print(f"Next: cd {args.dest} && docker compose up --build -d, then "
          f"docker compose run --rm --entrypoint python cli smoke.py http://{names['agent']}-agent:8000"
          + (f"; web UI on http://localhost:{names['port']}" if "web" in enabled else ""))


def cmd_add_agent(args) -> None:
    compose, init_sql = args.dest / "compose.yaml", args.dest / "postgres" / "init.sql"
    if not compose.is_file() or not init_sql.is_file():
        sys.exit(f"{args.dest} doesn't look like a project made by this scaffold (no compose.yaml / postgres/init.sql)")
    names = agent_names(args.agent, args.agent_title, args.agent_description)
    folder = args.dest / "agent" / "agents" / names["agent"]
    if folder.exists():
        sys.exit(f"{folder} already exists")
    enabled = {"mcp"} if args.mcp else set()
    copy_tree(TEMPLATES / "core" / "agent" / "agents", args.dest / "agent" / "agents", enabled, names)
    if args.mcp:
        copy_tree(TEMPLATES / "mcp" / "agent" / "agents", args.dest / "agent" / "agents", enabled, names)

    text = compose.read_text()
    if COMPOSE_MARK not in text:
        sys.exit(f"compose.yaml has no line {COMPOSE_MARK.strip()!r}; add the service by hand")
    block = (f"  {names['agent']}-agent:\n    <<: *agent\n    environment:\n      <<: *model-env\n"
             f"      AGENT_CONFIG: agents/{names['agent']}\n"
             f"      DATABASE_URL: postgresql://postgres:postgres@pgbouncer:6432/{names['agent_db']}\n"
             f"      PUBLIC_URL: http://{names['agent']}-agent:8000\n\n")
    compose.write_text(text.replace(COMPOSE_MARK, block + COMPOSE_MARK))
    sql = init_sql.read_text()
    init_sql.write_text(sql.replace(SQL_MARK, f"CREATE DATABASE {names['agent_db']};\n{SQL_MARK}"))
    print(f"Added agent '{names['agent']}': {folder.relative_to(args.dest)}/, a service in compose.yaml, "
          f"a database in postgres/init.sql.")
    print("init.sql only runs on a new volume. On a running project, create the database first:\n"
          f'  docker compose exec postgres psql -U postgres -c "CREATE DATABASE {names["agent_db"]}"\n'
          f"then: docker compose up --build -d {names['agent']}-agent && "
          f"docker compose run --rm --entrypoint python cli smoke.py http://{names['agent']}-agent:8000")


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(dest="command", required=True)
    new = sub.add_parser("new", help="render a new project")
    new.add_argument("dest", type=Path)
    new.add_argument("--name", required=True, help="kebab-case project name, e.g. it-agents")
    new.add_argument("--title", help="display name of the project")
    new.add_argument("--agent", default="assistant", help="kebab-case name of the first agent (default: assistant)")
    new.add_argument("--agent-title", help='e.g. "Helpdesk agent"')
    new.add_argument("--agent-description", help="one sentence: what the agent does")
    new.add_argument("--without", default="", help="comma separated modules to leave out: mcp, web")
    new.add_argument("--model", default="openai:azure-gpt-6-luna", help="LangChain provider:model")
    new.add_argument("--model-base-url", default="http://host.docker.internal:4000/v1",
                     help="OpenAI-compatible endpoint (an AI gateway on the host by default)")
    new.add_argument("--latest", action="store_true", help="resolve the newest releases instead of the verified ones")
    add = sub.add_parser("add-agent", help="add an agent to an existing project")
    add.add_argument("dest", type=Path)
    add.add_argument("--agent", required=True)
    add.add_argument("--agent-title")
    add.add_argument("--agent-description")
    add.add_argument("--mcp", action="store_true", help="give it the MCP server and the sample save_note tool")
    args = p.parse_args()
    cmd_new(args) if args.command == "new" else cmd_add_agent(args)


if __name__ == "__main__":
    main()
