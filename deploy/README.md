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

For production deployment on Streamlit Cloud:

1. **Configure Supabase**:
   - Create a Supabase project
   - Run the SQL script in `supabase/schema.sql`
   - Get your project URL and anon key

2. **Set up Streamlit Secrets**:
   - In Streamlit Cloud, add these secrets:
     ```
     [supabase]
     url = "your_supabase_project_url"
     key = "your_supabase_anon_key"
     ```

3. **Deploy**:
   - Connect your GitHub repo to Streamlit Cloud
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
