FROM ghcr.io/astral-sh/uv:python3.11-bookworm

WORKDIR /app

COPY pyproject.toml ./
RUN uv sync --frozen || uv sync

COPY . .

EXPOSE 8501

ENV STREAMLIT_BROWSER_GATHER_USAGE_STATS=false

CMD ["uv", "run", "streamlit", "run", "app.py", "--server.port=8501", "--server.address=0.0.0.0"]

