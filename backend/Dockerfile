FROM ghcr.io/astral-sh/uv:python3.11-bookworm

WORKDIR /app

# Copy dependency file(s) and install
COPY pyproject.toml ./
RUN uv sync --frozen || uv sync

# Copy source
COPY . .

ENV PYTHONUNBUFFERED=1
EXPOSE 8000

CMD ["uv", "run", "python", "manage.py", "runserver", "0.0.0.0:8000"]

