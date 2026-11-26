# One Dockerfile for all three Python services; compose passes the folder.
FROM python:3.13-slim
COPY --from=ghcr.io/astral-sh/uv:0.13.4 /uv /bin/uv
ARG SERVICE
WORKDIR /app
COPY ${SERVICE}/pyproject.toml ${SERVICE}/uv.lock ./
RUN uv sync --frozen --no-dev --no-install-project
COPY ${SERVICE}/ ./
ENV PATH="/app/.venv/bin:$PATH" PYTHONUNBUFFERED=1
