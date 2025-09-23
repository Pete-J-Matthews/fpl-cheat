# FPL Cheat

Compare your Fantasy Premier League team with content creators.

## Quick Start

```bash
git clone <your-repo-url>
cd fpl-cheat
make dev
```

- Frontend: http://localhost:8501
- Backend: http://localhost:8000/health/

## Commands

```bash
make dev     # Start development
make prod    # Deploy to Vercel
make logs    # View logs
make stop    # Stop services
make clean   # Clean up
```

## Manual Development

```bash
# Install dependencies
uv sync

# Run services
uv run python manage.py runserver  # Backend
uv run streamlit run app.py        # Frontend
```

## Production

1. Set up Supabase database
2. Add environment variables to Vercel
3. Run `make prod`

## Tech Stack

- Frontend: Streamlit
- Backend: Django
- Database: SQLite (local) / Supabase (prod)
- Deployment: Vercel
- Python: uv