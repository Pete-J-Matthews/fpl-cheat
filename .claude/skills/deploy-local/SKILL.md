---
name: deploy-local
description: Run FPL Cheat locally in Docker (app + throwaway Postgres) and verify it is healthy. Use when asked to start, run, deploy, or smoke-test the app locally, to check whether the local stack is healthy, or when the local containers won't come up (port clashes, unhealthy app, empty database, missing tables).
---

# Deploy FPL Cheat locally and check it's healthy

## What you're starting

There is no compose file. Two plain containers on a shared network:

- **app** — built from `deploy/Dockerfile`. A two-stage build: `uv sync --locked --no-dev` into `/opt/venv`
  in a uv image, then that venv copied into `python:3.12-slim-bookworm`. Entrypoint is
  `streamlit run app.py --server.port=8501 --server.address=0.0.0.0`. It is a plain server — it does not
  supervise anything, and any non-zero exit is a real fault.
- **db** — a throwaway `postgres:17`. It starts **completely empty**: no tables, no init scripts.

The container port is fixed at 8501. The flags in the ENTRYPOINT outrank `STREAMLIT_SERVER_PORT`, so only the
*host* side of `-p` is variable.

## Bring it up

Build context is the repo root, not `deploy/` — the Dockerfile bind-mounts `pyproject.toml` and `uv.lock` and
then does `COPY . .`:

```bash
docker build -f deploy/Dockerfile -t fpl-cheat:local .
```

```bash
docker network create fpl 2>/dev/null

docker run -d --name fpl-db --network fpl \
  -e POSTGRES_USER=fpl -e POSTGRES_PASSWORD=localdev -e POSTGRES_DB=fpl \
  postgres:17

docker run -d --name fpl-app --network fpl -p 127.0.0.1:8501:8501 \
  -e DATABASE_URL="postgresql://fpl:localdev@fpl-db:5432/fpl" \
  fpl-cheat:local
```

App is then on <http://127.0.0.1:8501>.

`DATABASE_URL` is the only required variable — `app/database.py:24` raises `RuntimeError` without it. Nothing
in the code reads `.env`; there is no `python-dotenv` dependency.

**Never point `DATABASE_URL` at production.** `app/scheduler.py` starts an APScheduler job on app startup that
*writes* `creator_teams` at 17:00 and 00:00 UK time. Production's Postgres is private
(`postgres.railway.internal`) and unreachable from a laptop anyway.

### If a port is already bound

`failed to bind port 127.0.0.1:8501` means something else holds it. Change the host side only:

```bash
docker run -d --name fpl-app --network fpl -p 127.0.0.1:8600:8501 ... fpl-cheat:local
```

## Verify it's healthy

Run in order; each rules out a different failure.

**1. Container healthy**

```bash
docker inspect --format '{{.State.Health.Status}}' fpl-app
```

Expect `healthy` (allow ~10s start period). The `HEALTHCHECK` in `deploy/Dockerfile` fetches
`/_stcore/health` with `urllib` — `curl` is deliberately not installed in the slim image.

**2. Streamlit is serving**

```bash
python -c "import urllib.request; r=urllib.request.urlopen('http://127.0.0.1:8501/_stcore/health',timeout=5); print(r.status, r.read())"
```

`200 b'ok'` is the real health signal.

**3. Logs**

```bash
docker logs -f fpl-app
```

Expect Streamlit's `You can now view your Streamlit app in your browser.` banner. `PYTHONUNBUFFERED=1` is set,
so output is not block-buffered.

**4. Database reachable from the app**

```bash
docker exec -e PGPASSWORD=localdev fpl-db psql -U fpl -d fpl -c 'select 1'
```

To test the app's own connection path — credentials, networking, psycopg2 — without depending on a schema
(note `--entrypoint`, see gotcha below):

```bash
docker run --rm --network fpl --entrypoint python \
  -e DATABASE_URL="postgresql://fpl:localdev@fpl-db:5432/fpl" \
  fpl-cheat:local -c "from app.database import get_connection
with get_connection() as c:
    cur = c.cursor(); cur.execute('select 1'); print('db ok:', cur.fetchone())"
```

Do **not** use `search_managers()` for this check — on a fresh database it raises
`psycopg2.errors.UndefinedTable: relation "all_managers" does not exist`, which looks like a connection
failure but is just the empty-schema state described below.

### Gotcha: ENTRYPOINT swallows arguments

`ENTRYPOINT ["streamlit", "run", "app.py", ...]` is exec form, so anything you append becomes a *Streamlit*
argument. `docker run fpl-cheat:local ls` tries `streamlit run app.py ls` and fails with
`Error: No such option`. Use `--entrypoint sh` / `--entrypoint python` to run anything else.

## What is expected to be broken locally

The local database is empty and **has no tables at all** — there are no init scripts. This is not a deployment
fault:

- **Search errors or returns nothing.** `all_managers` does not exist until something creates it.
  `scripts/fetch_fpl_data.py` creates its own tables on startup, so running it once fixes the schema. Its
  argument is a *mode*, not an environment: `local` writes to a SQLite file the app never reads, so the
  Postgres path is `production`. It is slow — it pages the public overall-standings endpoint.

  ```bash
  DATABASE_URL="postgresql://fpl:localdev@127.0.0.1:5432/fpl" \
    uv run python scripts/fetch_fpl_data.py production
  ```

  Note that script shells out to `curl` (`scripts/fetch_fpl_data.py:90`), which is **not** in the image — run
  it on the host, as above, not inside the container.

  Also: `search_managers()` needs a 4+ character prefix. Entering a manager ID directly works regardless,
  since picks come from the public FPL API rather than the database.

- **No creator comparison.** `creator_teams` has **no DDL anywhere in the repo** — `app/database.py:149`
  builds its INSERT column list dynamically from whatever dict it is handed, so the schema exists only in the
  deployed database. `get_creator_teams()` surfaces "Failed to get creator teams". To fix, dump it from inside
  Railway and load it locally:

  ```bash
  railway ssh -s fpl-cheat 'pg_dump --schema-only --table=creator_teams "$DATABASE_URL"' > /tmp/creator_teams.sql
  docker exec -i -e PGPASSWORD=localdev fpl-db psql -U fpl -d fpl < /tmp/creator_teams.sql
  ```

FPL API calls work immediately — the container has outbound network and needs no credentials.

## Tear down

```bash
docker rm -f fpl-app fpl-db
docker network rm fpl
```

The database is not persisted to a named volume, so removing `fpl-db` drops the data.

## Without Docker

`mise` points at `.venv`, so `uv run streamlit run app.py` works too — you just have to supply `DATABASE_URL`
yourself. See the README for running scripts against production inside Railway over SSH.
