# FPL Cheat ⚽

A Streamlit app that compares your Fantasy Premier League team with content creator teams to find similarities and the best match.

## Features

- 🔍 **Team Search**: Find your FPL team by name
- 📊 **Similarity Analysis**: Compare your squad with content creator teams
- 🏆 **Best Match**: Discover which creator team is most similar to yours
- 👥 **Creator Management**: Add and manage content creator teams
- 📈 **Leaderboard**: See similarity scores across all creators

## Quick Start

### Prerequisites

- Python 3.9+
- [uv](https://docs.astral.sh/uv/) for dependency management
- Supabase account (free tier available) - **only for production**

### Installation

1. **Clone the repository**
   ```bash
   git clone <your-repo-url>
   cd fpl-cheat
   ```

2. **Install dependencies**
   ```bash
   uv sync
   ```

3. **Set up local development (SQLite)**
   ```bash
   # Quick setup (recommended)
   ./deploy/setup.sh
   
   # Or manual setup
   python3 deploy/local_setup.py
   
   # Run the app locally
   uv run streamlit run app.py
   ```

4. **Set up production (Supabase) - Optional**
   ```bash
   # Create .streamlit/secrets.toml file
   mkdir -p .streamlit
   cat > .streamlit/secrets.toml << EOF
   [supabase]
   url = "your_supabase_project_url_here"
   key = "your_supabase_anon_key_here"
   EOF
   ```
   
   - Create a new Supabase project
   - Run the SQL script in `supabase/schema.sql` to create the required tables
   - Update the secrets.toml file with your credentials

## Database Setup

### Local Development (SQLite)

The app automatically uses SQLite for local development. Use the automated setup script:

```bash
# Quick setup (recommended)
./deploy/setup.sh

# Or run the Python setup directly
python3 deploy/local_setup.py
```

The setup script will:
- Check prerequisites (Python 3.9+, uv)
- Install all dependencies
- Create SQLite database with sample data
- Configure Streamlit for local development
- Verify everything works correctly

### Production (Supabase)

Create the following table in your Supabase project:

```sql
-- Create creator_teams table
CREATE TABLE creator_teams (
    id SERIAL PRIMARY KEY,
    team_name TEXT NOT NULL,
    squad_data JSONB NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Create index for better performance
CREATE INDEX idx_creator_teams_team_name ON creator_teams(team_name);
```

### Getting Supabase Credentials

1. Go to your Supabase project dashboard
2. Navigate to Settings > API
3. Copy the Project URL and anon/public key
4. Add them to your `.env` file

## Usage

### Team Comparison

1. Enter your FPL team name in the search box
2. The app will fetch your current squad
3. Compare with stored creator teams
4. View similarity scores and best match

### Managing Creator Teams

1. Go to "Manage Creators" in the sidebar
2. Add new creator teams by entering their FPL team name
3. View and manage existing creator teams

## Deployment

### Streamlit Community Cloud

1. Push your code to GitHub
2. Connect your GitHub repo to Streamlit Cloud
3. Add your Supabase credentials as secrets in Streamlit Cloud
4. Deploy!

### Environment Variables for Deployment

In Streamlit Cloud, add these secrets:
- `SUPABASE_URL`: Your Supabase project URL
- `SUPABASE_ANON_KEY`: Your Supabase anon key

## API Rate Limits

The app respects FPL API rate limits with built-in caching:
- Bootstrap data: 5-minute cache
- Team squads: 1-minute cache
- Automatic retry with exponential backoff

## Development

### Running in Development

```bash
# Install development dependencies
uv sync --extra dev

# Run with auto-reload
uv run streamlit run app.py --server.runOnSave true

# Run tests
uv run pytest

# Format code
uv run black .

# Lint code
uv run flake8 .
```

### Project Structure

```
fpl-cheat/
├── app.py              # Main Streamlit application
├── database.py         # Database abstraction layer (SQLite/Supabase)
├── pyproject.toml      # Dependencies and project config
├── README.md           # This file
├── fpl_cheat.db        # Local SQLite database (created by setup)
├── deploy/             # Deployment and setup scripts
│   ├── setup.sh        # Quick setup script
│   ├── local_setup.py  # Comprehensive setup script
│   └── README.md       # Deployment documentation
└── supabase/
    └── schema.sql      # Supabase database schema
```

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests if applicable
5. Submit a pull request

## License

MIT License - see LICENSE file for details

## Support

If you encounter any issues:
1. Check the troubleshooting section below
2. Open an issue on GitHub
3. Check FPL API status

## Troubleshooting

### Common Issues

**"Team not found" error:**
- Ensure the team name matches exactly as it appears in FPL
- Check for typos and case sensitivity

**"Supabase connection failed":**
- Verify your credentials in `.env`
- Check if your Supabase project is active
- Ensure the database schema is set up correctly

**"Failed to fetch FPL data":**
- Check your internet connection
- FPL API might be temporarily down
- Try again in a few minutes

### Performance Tips

- The app caches data to reduce API calls
- Clear cache by restarting the app if needed
- Consider adding more creator teams for better comparisons
