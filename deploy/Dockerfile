# ---BUILD STAGE---
FROM ghcr.io/astral-sh/uv:python3.12-bookworm-slim AS builder

# UV optimisation parameters
ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_PYTHON_DOWNLOADS=never \
    UV_PROJECT_ENVIRONMENT=/opt/venv

WORKDIR /app

# Copy only the lockfile inputs first, so editing application code doesn't
# invalidate this layer. Railway's builder supports no mount type other than
# type=cache, so BuildKit bind/cache mounts can't be used here at all. These
# files stay in the builder stage, which is discarded -- only /opt/venv is
# carried into the runtime image.
COPY pyproject.toml uv.lock ./

RUN uv sync --locked --no-dev


# --- RUNTIME STAGE ---
FROM python:3.12-slim-bookworm AS runtime

RUN useradd --system --create-home --uid 1001 app

WORKDIR /app

COPY --from=builder /opt/venv /opt/venv

# Port/address are env vars, not CLI flags: Streamlit ranks flags above env,
# so a hardcoded --server.port could not be overridden at runtime. Railway's
# domain targets 8080, so it sets STREAMLIT_SERVER_PORT=8080 as a service
# variable. ECS leaves it unset and gets the 8501 default.
ENV PATH="/opt/venv/bin:$PATH" \
    PYTHONUNBUFFERED=1 \
    STREAMLIT_SERVER_PORT=8501 \
    STREAMLIT_SERVER_ADDRESS=0.0.0.0 \
    STREAMLIT_SERVER_HEADLESS=true \
    STREAMLIT_BROWSER_GATHER_USAGE_STATS=false

COPY --chown=app:app . .

USER app

EXPOSE 8501

# Reads the same env var the server binds to, so the check follows a port
# override instead of probing a dead 8501.
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD python -c "import os, urllib.request; urllib.request.urlopen('http://127.0.0.1:' + os.environ['STREAMLIT_SERVER_PORT'] + '/_stcore/health')"

ENTRYPOINT ["streamlit", "run", "app.py"]
