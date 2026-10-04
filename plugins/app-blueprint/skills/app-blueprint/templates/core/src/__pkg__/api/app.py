from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import APIRouter, FastAPI
{{#frontend}}
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
{{/frontend}}
{{#db}}
from sqlalchemy.orm import sessionmaker
{{/db}}

{{#auth}}
from .. import auth
{{/auth}}
from ..config import Settings, get_settings
from ..middleware import RequestContext
{{#db}}
from ..db import make_engine, run_migrations
from . import notes
{{/db}}
from .errors import ApiError, install_handlers

ROOT = Path(__file__).resolve().parents[3]  # the repository (or /app in the image): alembic.ini, frontend/dist


def create_app(
    settings: Settings | None = None,
{{#auth}}
    workos: auth.WorkOSAuth | None = None,
{{/auth}}
) -> FastAPI:
    settings = settings or get_settings()

    @asynccontextmanager
{{#db}}
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
{{/db}}
{{^db}}
    async def lifespan(_app: FastAPI) -> AsyncIterator[None]:
{{/db}}
{{#db}}
        run_migrations(settings)
        engine = make_engine(settings)
        app.state.session_factory = sessionmaker(engine, expire_on_commit=False)
        try:
            yield
        finally:
            engine.dispose()
{{/db}}
{{^db}}
        yield
{{/db}}

    app = FastAPI(
        title="{{title}}",
        openapi_url="/api/openapi.json",
        docs_url="/api/docs",
        lifespan=lifespan,
        # operation ids are the handlers' names: the generated client gets listNotes(), not listNotesApiNotesGet()
        generate_unique_id_function=lambda route: route.name,
    )
    app.state.settings = settings
    install_handlers(app)
{{#auth}}
    app.state.workos = None
    if settings.auth_enabled:
        app.state.workos = workos or auth.SdkWorkOS(settings)
        app.add_middleware(auth.AuthMiddleware)
        app.include_router(auth.build_router())
{{/auth}}
    app.add_middleware(RequestContext)  # added last, so it runs first: every response gets its id and headers

    api = APIRouter(prefix="/api")

    @api.get("/health")
    async def health() -> dict[str, str]:
        return {"status": "ok"}
{{#auth}}

    api.include_router(auth.me_router)
{{/auth}}
{{#db}}
    api.include_router(notes.router)
{{/db}}
    app.include_router(api)
{{#frontend}}
    _serve_frontend(app, ROOT / "frontend" / "dist")
{{/frontend}}
    return app
{{#frontend}}


def _serve_frontend(app: FastAPI, dist: Path) -> None:
    """The built SPA: real files as they are, every other path gets index.html (the router takes it from there)."""
    if not dist.is_dir():
        return  # not built (tests, or `npm run dev` serves it)
    app.mount("/assets", StaticFiles(directory=dist / "assets"), name="assets")

    @app.api_route("/{path:path}", methods=["GET", "HEAD"], include_in_schema=False)
    async def spa(path: str) -> FileResponse:
        if path == "api" or path.startswith("api/"):
            raise ApiError("not_found", f"No API endpoint /{path}", 404)  # never the SPA for a mistyped API call
        file = (dist / path).resolve()
        if path and file.is_file() and file.is_relative_to(dist.resolve()):
            return FileResponse(file)
        return FileResponse(dist / "index.html", headers={"Cache-Control": "no-cache"})
{{/frontend}}
