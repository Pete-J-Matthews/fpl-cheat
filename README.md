# FPL Cheat ⚽

A Streamlit app that compares your Fantasy Premier League team with content creator teams to find similarities and the best match.

## Features

- 🔍 **Smart Team Search**: Search by team name, manager name, or manager ID
- 📊 **Similarity Analysis**: Compare with 21+ content creator teams
- ⚽ **Visual Pitch Display**: Side-by-side team comparison with jersey images
- 🔄 **Auto-Updates**: Creator teams update at 5pm and midnight UK time
- 💾 **Smart Caching**: Built-in caching to respect FPL API rate limits

## Architecture

The app is deployed on Railway with a PostgreSQL database. Railway automatically provides the `DATABASE_URL` environment variable when a PostgreSQL service is added. The app uses `Procfile` and `railway.toml` for deployment configuration. A background scheduler runs automatically to update creator teams at 5pm and midnight UK time.

## Database
FPL Managers database is populated by scraping the public api endpoint. This extracts the Manager name, 
Team name and Manager ID. The ID is required for accessing each managers api endpoint and so the lookup
search bar was created to facilitate this. 


## Usage

1. Search for your team (name, manager name, or manager ID - min 4 chars for names)
2. Click "Compare Teams" to find top 3 similar creator teams
3. Select a creator team to see side-by-side comparison with jersey images

## Troubleshooting

**"Team not found"**: Enter manager ID directly or use 4+ character search  
**"Database connection failed"**: Verify `DATABASE_URL` in Railway  
**"No creator teams"**: Wait for scheduled update (5pm/midnight UK)  
**"Query timeout"**: Use longer search terms or manager ID directly

## License

MIT License
