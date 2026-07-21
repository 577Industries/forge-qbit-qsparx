FROM ghcr.io/astral-sh/uv:0.11.16 AS uv

FROM python:3.14-slim AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    PATH="/app/.venv/bin:$PATH"

COPY --from=uv /uv /uvx /bin/
WORKDIR /app
COPY pyproject.toml uv.lock README.md LICENSE NOTICE ./
COPY src ./src
RUN uv sync --frozen --no-dev --no-editable && \
    useradd --create-home --uid 10001 qsparx && \
    chown -R qsparx:qsparx /app

USER 10001
EXPOSE 8775
HEALTHCHECK --interval=30s --timeout=3s --start-period=10s --retries=3 \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8775/openapi.json', timeout=2)" || exit 1

CMD ["uvicorn", "forge_qsparx.api:app", "--host", "0.0.0.0", "--port", "8775"]
