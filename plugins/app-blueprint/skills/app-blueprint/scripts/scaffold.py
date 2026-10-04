#!/usr/bin/env python3
"""Render a new app from the blueprint templates, then install current versions of its packages.

    scaffold.py DEST --name my-app [--title "My App"] [--without frontend,db,azure] [--with auth] [--no-install]

Modules (each a folder in ../templates, plus {{#module}} ... {{/module}} blocks in shared files):
  core      always: FastAPI backend, uv, ruff, pyright, pytest, scripts/check.sh, CLAUDE.md, CI, Dockerfile
  frontend  React + Vite + TypeScript + Tailwind + TanStack Query, API client generated from OpenAPI  (default on)
  db        PostgreSQL in a local container, SQLAlchemy 2, Alembic                                       (default on)
  auth      WorkOS AuthKit sign-in with the app's own session cookie                                     (default off)
  azure     Bicep + scripts/azure-up.sh / azure-down.sh for Azure Container Apps                         (default on)

Template syntax, in file contents and paths:
  {{app}} my-app   {{pkg}} my_app   {{title}} My App   {{pg_port}} a port per app, so projects don't clash
  __pkg__ in a path becomes the package name. A line holding {{#m}} / {{/m}} opens / closes a block kept only with
  module m; {{^m}} / {{/m}} a block kept only without it. Marker lines themselves are dropped. Opened and closed on
  one line ("PostgreSQL{{#auth}} and WorkOS{{/auth}}"), the block is just that phrase.

Versions are never pinned here: --no-install skips `uv add` / `npm install`, which pick the latest releases.
Used with --no-install into a scratch folder, it also renders a reference project to diff against an existing repo.
"""

import argparse
import re
import shutil
import subprocess
import sys
import zlib
from pathlib import Path

TEMPLATES = Path(__file__).resolve().parent.parent / "templates"
MODULES = ("frontend", "db", "auth", "azure")
DEFAULT_ON = {"frontend", "db", "azure"}

PY_DEPS = {
    "core": ["fastapi", "uvicorn[standard]", "pydantic-settings"],
    "db": ["sqlalchemy", "alembic", "psycopg[binary]"],
    "auth": ["workos"],
    "db+azure": ["azure-identity"],  # PostgreSQL with Entra tokens on Azure
}
PY_DEV_DEPS = ["pytest", "httpx2", "ruff", "pyright"]  # httpx2: what starlette's TestClient uses
NPM_DEPS = [
    "react", "react-dom", "react-router", "@tanstack/react-query",
    "tailwindcss", "@tailwindcss/vite", "@fontsource-variable/inter", "lucide-react", "sonner", "clsx", "tailwind-merge",
]  # fmt: skip
NPM_DEV_DEPS = [
    # TypeScript 7 (the native port) has no JavaScript compiler API yet, which the API client generator needs
    "vite", "@vitejs/plugin-react", "typescript@^6", "@types/react", "@types/react-dom", "@types/node",
    "@hey-api/openapi-ts", "oxlint", "prettier",
]  # fmt: skip

MARKER = re.compile(r"\{\{([#^/])(\w+)\}\}")
INLINE = re.compile(r"\{\{([#^])(\w+)\}\}(.*?)\{\{/\2\}\}")


def render(text: str, enabled: set[str], names: dict[str, str]) -> str:
    # a block that opens and closes on one line is a phrase inside the line; any other marker owns its line
    text = INLINE.sub(lambda m: m[3] if (m[2] in enabled) == (m[1] == "#") else "", text)
    out, stack = [], []  # stack of (module, keep_when_enabled)
    for line in text.splitlines(keepends=True):
        m = MARKER.search(line)
        if m:
            if not re.fullmatch(r"\s*(#|//|<!--)?\s*" + re.escape(m[0]) + r"\s*(-->)?\s*", line):
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


def copy_module(module: str, dest: Path, enabled: set[str], names: dict[str, str]) -> None:
    src = TEMPLATES / module
    for path in sorted(src.rglob("*")):
        if path.is_dir() or "__pycache__" in path.parts:
            continue
        rel = str(path.relative_to(src)).replace("__pkg__", names["pkg"])
        target = dest / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        try:
            target.write_text(render(path.read_text(), enabled, names))
        except UnicodeDecodeError:  # binary: copy as is
            shutil.copyfile(path, target)
        target.chmod(path.stat().st_mode)


def run(cmd: list[str], cwd: Path) -> None:
    print("+", " ".join(cmd), flush=True)
    if subprocess.run(cmd, cwd=cwd).returncode:
        sys.exit(f"failed: {' '.join(cmd)} (in {cwd}); the files are rendered, fix the cause and rerun the rest")


def uv_build_requirement() -> str:
    """uv_build pinned to the installed uv's minor version, as `uv init` does."""
    out = subprocess.run(["uv", "--version"], capture_output=True, text=True, check=True).stdout
    major, minor, patch = re.search(r"(\d+)\.(\d+)\.(\d+)", out).groups()
    return f"uv_build>={major}.{minor}.{patch},<{major}.{int(minor) + 1}.0"


def install(dest: Path, enabled: set[str]) -> None:
    run(["git", "init", "-q", "-b", "main"], dest)
    deps = [d for key, ds in PY_DEPS.items() if key == "core" or set(key.split("+")) <= enabled for d in ds]
    run(["uv", "add", "--quiet", *deps], dest)
    run(["uv", "add", "--quiet", "--dev", *PY_DEV_DEPS], dest)
    if "frontend" in enabled:
        web = dest / "frontend"
        run(["npm", "install", "--silent", "--no-fund", "--no-audit", *NPM_DEPS], web)
        run(["npm", "install", "--silent", "--no-fund", "--no-audit", "--save-dev", *NPM_DEV_DEPS], web)
        run(["npm", "run", "--silent", "gen:api"], web)
        run(["npm", "run", "--silent", "format"], web)
    run(["uv", "run", "--quiet", "ruff", "check", "--fix", "--quiet", "."], dest)
    run(["uv", "run", "--quiet", "ruff", "format", "--quiet", "."], dest)


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("dest", type=Path)
    p.add_argument("--name", required=True, help="kebab-case, e.g. invoice-hub")
    p.add_argument("--title", help='display name, default from --name ("Invoice Hub")')
    p.add_argument("--with", dest="with_", default="", help="comma separated modules to add (e.g. auth)")
    p.add_argument("--without", default="", help="comma separated modules to leave out (e.g. azure)")
    p.add_argument("--no-install", action="store_true", help="only render the files")
    args = p.parse_args()

    if not re.fullmatch(r"[a-z][a-z0-9]*(-[a-z0-9]+)*", args.name):
        sys.exit("--name must be kebab-case: lowercase letters, digits and dashes")
    asked = {m for m in f"{args.with_},{args.without}".split(",") if m}
    if unknown := asked - set(MODULES):
        sys.exit(f"unknown modules: {', '.join(sorted(unknown))} (known: {', '.join(MODULES)})")
    enabled = (DEFAULT_ON | set(filter(None, args.with_.split(",")))) - set(args.without.split(","))
    if args.dest.exists() and any(args.dest.iterdir()):
        sys.exit(f"{args.dest} exists and is not empty")

    names = {
        "app": args.name,
        "pkg": args.name.replace("-", "_"),
        "title": args.title or args.name.replace("-", " ").title(),
        # a stable port per app, so several projects' databases can run side by side
        "pg_port": str(54320 + zlib.crc32(args.name.encode()) % 600),
        "uv_build": uv_build_requirement() if not args.no_install else "uv_build",
    }
    args.dest.mkdir(parents=True, exist_ok=True)
    for module in ("core", *MODULES):
        if (module == "core" or module in enabled) and (TEMPLATES / module).is_dir():
            copy_module(module, args.dest, enabled, names)
    print(f"Rendered {names['app']} in {args.dest} with: {', '.join(m for m in MODULES if m in enabled) or 'core only'}")
    if not args.no_install:
        install(args.dest, enabled)
    print("Next: " + ("scripts/db.sh up, then " if "db" in enabled else "") + "scripts/check.sh, then scripts/run-local.sh")


if __name__ == "__main__":
    main()
