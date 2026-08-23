# FPL Cheat ⚽

A Streamlit app that compares your Fantasy Premier League team with content creator teams to find similarities and your closest matches.

## Features

- 🔍 **Smart Team Search**: Search by team name, manager name, or manager ID
- 📊 **Similarity Analysis**: Compare with 31 creator teams and see the top 3 matches
- ⚽ **Visual Pitch Display**: Side-by-side team comparison with jersey images and shared-player highlighting
- 🔄 **Auto-Updates**: Creator teams update at 5pm and midnight UK time while the app process is running
- 💾 **Smart Caching**: Streamlit caching for FPL API calls to reduce repeat requests

## Architecture

The app is deployed on Railway with a PostgreSQL database. Railway provides the `DATABASE_URL` environment variable when a PostgreSQL service is attached. The app is containerised: `deploy/Dockerfile` defines the image and `railway.toml` points Railway at it. An in-app APScheduler background job updates creator teams at 5pm and midnight UK time.

Build locally with the repo root as the context:

```bash
docker build -f deploy/Dockerfile -t fpl-cheat:local .
docker run --rm -p 8501:8501 -e DATABASE_URL="postgresql://..." fpl-cheat:local
```

### Database networking

The PostgreSQL service is **private**. It has no public TCP proxy, so it is only reachable over Railway's
private network at `postgres.railway.internal:5432`. The app service picks this up automatically via
`DATABASE_URL`; nothing outside the Railway project can connect.

This means database work cannot be run from a laptop against production — it has to run *inside* Railway
(see [Running data loads](#running-data-loads) below).

## Database
The manager lookup database (`all_managers`) is populated from the public FPL overall league standings endpoint using `scripts/fetch_fpl_data.py`. This stores manager name, team name, and manager ID for search. Creator comparison squads are stored separately in `creator_teams` (player_1 to player_15 plus current gameweek).

### Running data loads

Because the database is private, one-off scripts run inside the deployed service over SSH:

```bash
# One-time setup: register your SSH public key with Railway
railway ssh keys add

# Backfill the manager lookup table (long-running — use a tmux session so it
# survives a dropped connection)
railway ssh -s fpl-cheat --session fetch
# then, inside the shell:
python scripts/fetch_fpl_data.py production

# Ad-hoc psql
railway ssh -s fpl-cheat 'psql "$DATABASE_URL"'
```

Creator teams need no manual step — the in-app APScheduler job updates them on schedule.

Do **not** re-add a public TCP proxy to the database service to work around this. If you genuinely need
one temporarily, `railway tcp-proxy create --port 5432 -s fpl-cheat-db` adds it and
`railway tcp-proxy delete <id> -s fpl-cheat-db` removes it again — delete it as soon as you are done.


## Usage

1. Search for your team (team name, manager name, or manager ID - name/team search is prefix-based and works best with 4+ chars)
2. Your team is compared automatically against creator teams; top similar teams appear below
3. Select a creator team to see side-by-side comparison with jersey images and shared-player highlighting

## Troubleshooting

**"Failed to fetch picks" / "No picks found"**: Enter manager ID directly, then verify the ID exists for the current gameweek
**"Database credentials missing / connection failed"**: Verify `DATABASE_URL` is set and PostgreSQL is attached in Railway. From a laptop this error is expected — the database is private and `postgres.railway.internal` only resolves inside Railway
**"No creator teams available for gameweek X"**: Run `scripts/update_creator_teams_cron.py` or wait for the scheduled 5pm/midnight UK update while the app is running
**"No search results / query timeout"**: Use a longer search prefix (4+ chars) or enter manager ID directly

## License

MIT License
