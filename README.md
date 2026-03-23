# FPL Cheat ⚽

A Streamlit app that compares your Fantasy Premier League team with content creator teams to find similarities and your closest matches.

## Features

- 🔍 **Smart Team Search**: Search by team name, manager name, or manager ID
- 📊 **Similarity Analysis**: Compare with 31 creator teams and see the top 3 matches
- ⚽ **Visual Pitch Display**: Side-by-side team comparison with jersey images and shared-player highlighting
- 🔄 **Auto-Updates**: Creator teams update at 5pm and midnight UK time while the app process is running
- 💾 **Smart Caching**: Streamlit caching for FPL API calls to reduce repeat requests

## Architecture

The app is deployed on Railway with a PostgreSQL database. Railway provides the `DATABASE_URL` environment variable when a PostgreSQL service is attached. The app uses `Procfile` and `railway.toml` for deployment configuration. An in-app APScheduler background job updates creator teams at 5pm and midnight UK time.

## Database
The manager lookup database (`all_managers`) is populated from the public FPL overall league standings endpoint using `scripts/fetch_fpl_data.py`. This stores manager name, team name, and manager ID for search. Creator comparison squads are stored separately in `creator_teams` (player_1 to player_15 plus current gameweek).


## Usage

1. Search for your team (team name, manager name, or manager ID - name/team search is prefix-based and works best with 4+ chars)
2. Your team is compared automatically against creator teams; top similar teams appear below
3. Select a creator team to see side-by-side comparison with jersey images and shared-player highlighting

## Troubleshooting

**"Failed to fetch picks" / "No picks found"**: Enter manager ID directly, then verify the ID exists for the current gameweek  
**"Database credentials missing / connection failed"**: Verify `DATABASE_URL` is set and PostgreSQL is attached in Railway  
**"No creator teams available for gameweek X"**: Run `scripts/update_creator_teams_cron.py` or wait for the scheduled 5pm/midnight UK update while the app is running  
**"No search results / query timeout"**: Use a longer search prefix (4+ chars) or enter manager ID directly

## License

MIT License
