FPL Cheat

A simple app to compare your Fantasy Premier League squad to popular content creators.

Tech Stack
- Frontend: Streamlit
- Backend: Django + PostgreSQL (Supabase in prod)
- Environment/Deps: uv (Python 3.11)
- Containerization: Docker

Quick start (dev)

1) Create `.env` at repo root:

```
DJANGO_SECRET_KEY=change-me
DJANGO_DEBUG=true
DJANGO_ALLOWED_HOSTS=*
DATABASE_URL=
BACKEND_URL=http://localhost:8000
FPL_API_BASE=https://fantasy.premierleague.com/api
```

2) Build and run:

```bash
docker compose up --build
```

- Backend: http://localhost:8000/health/
- Frontend: http://localhost:8501

Directory structure
- `backend/`: Django project (`fpl_backend`)
- `frontend/`: Streamlit app (`app.py`)

Notes
- Postgres is expected to be managed (Supabase) for non-local; set `DATABASE_URL`.
- For local dev without Postgres, SQLite is used automatically.

## Deployment

### Frontend (Vercel)
1. Install Vercel CLI: `npm i -g vercel`
2. In `frontend/` directory: `vercel --prod`
3. Set environment variable: `BACKEND_URL` to your deployed backend URL
4. Your Vercel project: `pete-j-matthews-projects/fpl-cheat`

### Backend (Supabase + Hosting)
1. **Database**: Supabase Postgres configured
   - URL: `postgresql://postgres:Bonecruncher1@db.lttvknhtrgknkesxavbh.supabase.co:5432/postgres`
   - Set `DATABASE_URL` in your hosting environment
2. **Hosting**: Deploy Django to any container platform (Railway, Render, etc.)
3. **Environment Variables**:
   ```
   DATABASE_URL=postgresql://postgres:Bonecruncher1@db.lttvknhtrgknkesxavbh.supabase.co:5432/postgres
   DJANGO_SECRET_KEY=your-secret-key
   DJANGO_DEBUG=false
   DJANGO_ALLOWED_HOSTS=your-backend-domain.com
   ```

### Local Development
- Uses SQLite for simplicity
- Supabase connection available for production testing

