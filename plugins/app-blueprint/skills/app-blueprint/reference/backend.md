# Backend

## Layout

```
src/<pkg>/
  __init__.py      main(): logging, then uvicorn
  config.py        Settings (pydantic-settings), get_settings(), settings_without_env_file()
  api/app.py       create_app(settings): middleware, error handlers, routers, the SPA
  api/errors.py    ApiError, the error envelope, get_or_404
  api/<area>.py    one router per area (notes.py is the example)
  middleware.py    request ids, access log, security headers, JSON logging
  db.py, models.py (db module)   auth.py (auth module)   openapi.py (schema for the frontend's codegen)
```

The `src/` layout with `uv_build` keeps tests importing the installed package, not the working directory. A flat
layout grouped by kind (as in FastAPI's "Bigger Applications" docs) suits a small app. When the app grows past
~5 areas, or one area past ~400 lines, move to packages per domain (as in zhanymkanov/fastapi-best-practices):
`src/<pkg>/<area>/router.py, models.py, service.py, schemas.py`. Split earlier when a router starts holding
business logic: the router parses input and shapes output, and the logic goes into a plain module the router calls.
That module is testable without HTTP.

## Routes

- Use **sync `def` handlers with a sync SQLAlchemy `Session`**. FastAPI runs them in a threadpool (40 threads by
  default). Async SQLAlchemy only pays off at high concurrency, and it brings lazy-loading pitfalls. Use `async def`
  only for handlers that await something (httpx, SDK clients) and never block.
- Dependencies go through `Annotated` aliases (`SessionDep = Annotated[Session, Depends(get_session)]`). Ruff's
  `FAST002` enforces this.
- Every route has Pydantic models in and out (`NoteIn`, `NoteOut` with `from_attributes=True`). The return annotation
  is the response model, and it also names the generated TypeScript type.
- Operation ids are the handler names (`generate_unique_id_function=lambda route: route.name`), so name handlers
  well: `list_notes` becomes `listNotesOptions()` in the frontend. Names must be unique across the app.

## Errors

There is one envelope for every failure: `{"error": {"code", "message", ...}}`. Raise
`ApiError(code, message, status)` on purpose. Validation errors (`code: "invalid"`, with `fields`), 404/405 and
other `HTTPException`s are converted by handlers in `errors.py`, so the frontend handles a single shape. RFC 9457
Problem Details is the standard alternative; switch only if outside clients need it. Unknown `/api/...` paths are a
JSON 404 and never the SPA's `index.html`.

## Settings

All settings live in `config.py` (pydantic-settings, `.env` locally, real environment variables on Azure). Each is
documented in `.env.example`, and `tests/test_config.py` fails when one is missing there. Code receives `Settings`
(`create_app(settings)`, `app.state.settings`) and doesn't call `get_settings()` deep inside, so tests pass their
own. Tests use `settings_without_env_file()` so a developer's `.env` never leaks in.

## Logging and middleware

- `RequestContext` (plain ASGI, so streaming passes untouched) gives every request an id: the caller's
  `X-Request-ID` or a new one. The id goes into every log line and the response header, and the request is logged
  with status and duration.
- `LOG_JSON=true` (set by the Azure deploy) writes one JSON object per line, which Log Analytics can query by field.
  Locally the lines stay readable.
- Security headers: `nosniff`, `Referrer-Policy`, `X-Frame-Options`, plus a CSP on the SPA's HTML. `/api/docs` has no
  CSP because it loads Swagger UI from a CDN.
- Middleware order: the last one added runs first. `RequestContext` is added last, so even auth's 401s carry an id.

## Left out on purpose

- **CORS:** the SPA and the API share one origin. Add CORS only for a real cross-origin client.
- **Rate limiting:** add it to public, unauthenticated endpoints when the app gets them.
- **OpenTelemetry:** `azure-monitor-opentelemetry` is one call in `main()` when tracing is needed. Add it with the
  `APPLICATIONINSIGHTS_CONNECTION_STRING` setting and an Application Insights resource in `main.bicep`.
- **Background work:** for anything over a few seconds, use a queue. A Container Apps Job, or a worker app from
  `app.bicep`, beats threads in the web process once there is more than one replica.
