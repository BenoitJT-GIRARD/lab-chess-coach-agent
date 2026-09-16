# Backend image: FastAPI + LangGraph agent and its tools.
# Python 3.12 (matching .python-version) on a slim Debian base.
FROM python:3.12-slim

# System dependencies:
#  - stockfish: the chess engine queried by the evaluation service
#    (installed at /usr/games/stockfish, see STOCKFISH_PATH).
RUN apt-get update \
    && apt-get install -y --no-install-recommends stockfish \
    && rm -rf /var/lib/apt/lists/*

# uv provides fast, reproducible dependency installation from uv.lock.
COPY --from=ghcr.io/astral-sh/uv:0.11 /uv /uvx /bin/

WORKDIR /app

# uv installs into a project-local virtualenv; expose it on PATH.
ENV UV_PROJECT_ENVIRONMENT=/app/.venv \
    UV_COMPILE_BYTECODE=1 \
    PATH="/app/.venv/bin:$PATH"

# 1) Install third-party dependencies first (cached unless the lockfile changes).
COPY pyproject.toml uv.lock README.md ./
RUN uv sync --frozen --no-dev --no-install-project

# 2) Install the project itself.
COPY src ./src
COPY scripts ./scripts
RUN uv sync --frozen --no-dev

# The knowledge base, ingested into Milvus at runtime. The Wikichess articles are
# not redistributed: only their manifest is here, and docker-compose mounts the folder
# the download fills.
COPY data ./data

EXPOSE 8000

# The service runs as a named user, not as root. The two writable paths are prepared here so
# that the mounted volumes inherit an owner the process can write to: the Hugging Face cache,
# and the folder the Wikichess download fills.
RUN useradd --create-home --uid 1000 coach \
    && mkdir -p /cache/huggingface /app/data/wikichess \
    && chown -R coach:coach /app /cache
USER coach

# Lightweight liveness probe used by docker-compose.
HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
    CMD python -c "import urllib.request,sys; sys.exit(0 if urllib.request.urlopen('http://localhost:8000/api/v1/healthcheck').status==200 else 1)"

CMD ["uvicorn", "chess_coach.api.main:app", "--host", "0.0.0.0", "--port", "8000"]
