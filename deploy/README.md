# Deployment Scripts

This folder contains deployment and setup scripts for the FPL Cheat application.

## Local Development Setup

### Quick Setup

```bash
./deploy/setup.sh
```

### Manual Setup

```bash
python3 deploy/local_setup.py
```

### What the setup does:

1. Checks prerequisites (Python 3.9+, uv)
2. Installs dependencies via `uv sync`
3. Creates SQLite database with sample data
4. Configures Streamlit for local development

### After Setup:

```bash
uv run streamlit run app.py
# Open http://localhost:8501
```

## Production Deployment

For production deployment on Railway:

1. **Configure Supabase**:
   - Create a Supabase project
   - Run the SQL script in `supabase/schema.sql`
   - Get your project URL and anon key

2. **Set up Railway Environment Variables**:
   - In Railway project dashboard, go to "Variables"
   - Add these environment variables:
     - `SUPABASE_URL`: Your Supabase project URL
     - `SUPABASE_KEY`: Your Supabase anon key
   - Railway automatically sets `PORT` (no configuration needed)

3. **Deploy**:
   - Push your code to GitHub
   - Connect your GitHub repo to Railway
   - Railway will automatically detect the `Procfile` and deploy
   - The app will automatically use Supabase in production

## Database Behavior

- **Local Development**: Uses SQLite (`fpl_cheat.db`)
- **Production**: Uses Supabase (PostgreSQL)
- **Automatic Detection**: App detects environment and uses appropriate database

## Troubleshooting

### Common Issues:

**"uv not found"**:
```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

**"Python version too old"**:
- Install Python 3.9+ from python.org or your package manager

**"Database connection failed"**:
- Delete `fpl_cheat.db` and run setup again
- Check file permissions in the project directory

**"Streamlit won't start"**:
- Check if port 8501 is available
- Try: `uv run streamlit run app.py --server.port 8502`
