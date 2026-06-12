# Personal Tech Radar

Personal Tech Radar is the storage, scoring, and web publishing layer for a GeekNews-based daily digest.
It ingests prepared markdown summaries, stores issue metadata in SQLite, writes rendered markdown files, scores items against a personal radar profile, and serves the archive through a FastAPI backend plus Next.js frontend.

## Current scope

- Store daily GeekNews issue metadata in SQLite
- Store full rendered markdown under workspace content files
- Serve issue archive/detail APIs from FastAPI
- Render archive/detail UI from Next.js under `/technews`
- Provide the core platform for the Personal Tech Radar workflow

## Run locally

### Backend

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload --host 127.0.0.1 --port 8010
```

### Frontend

```bash
cd frontend
npm install
npm run dev
```

## Environment variables

### Backend

Configured in `backend/.env`.

Supported settings today:

- `APP_NAME`
- `APP_ENV`
- `DATABASE_URL`
- `CONTENT_ROOT`
- `INGEST_TOKEN`
- `TECH_RADAR_PROFILE_PATH`
- `TECH_RADAR_MIN_TELEGRAM_SCORE`
- `TECH_RADAR_IMPORTANT_SCORE`

### Frontend

Optional:

- `NEXT_PUBLIC_API_BASE_URL`

If unset in the browser, frontend uses same-origin `/technews-api`.

## Profile configuration

Phase 1 adds a Personal Tech Radar profile configuration file.

Default location:

- `config/tech-radar-profile.yaml`

Override with:

- `TECH_RADAR_PROFILE_PATH`

If your real profile is private, point `TECH_RADAR_PROFILE_PATH` at a file outside the repository and keep the checked-in YAML as a generic sample only.

Example structure:

```yaml
profile:
  interests:
    - AI Systems
    - Developer Tools
    - ML Infrastructure

  projects:
    - name: Workflow Automation Platform
      description: Multi-step agent and workflow orchestration backend
      keywords:
        - workflow orchestration
        - execution graph
```

Behavior:

- if the profile file exists and is valid, it is loaded
- if the file is missing, default fallback interests/projects are used
- if the file is malformed, the app falls back safely to defaults

At this phase, the profile loader is implemented as infrastructure for future scoring and matching work. Existing publishing behavior is unchanged.

## Phase 2 summary structure

Issue summaries now support structured fields in addition to the legacy `summary` string:

- `short_summary`
- `impact_summary`
- `action_items`
- `tags`
- `radar_category`
- `radar_status`

Compatibility behavior:

- legacy plain-text `summary` values still load safely
- API responses now expose structured summary fields
- if structured fields are missing or invalid, fallback values are generated and saved on ingest
- current ingest scripts provide safe default structured values even before LLM-based JSON generation is added

This keeps existing publishing behavior working while preparing for later scoring, radar, and Telegram formatting phases.

## Phase 3 importance scoring

Each issue now also carries score data in storage and API responses:

- `interest_score`
- `project_score`
- `novelty_score`
- `actionability_score`
- `credibility_score`
- `community_score`
- `final_score`
- `reason`
- `recommended_action`

Current implementation uses a safe fallback scorer rather than LLM scoring.
It derives a conservative score from:

- profile interest keywords
- project keyword matches
- summary tags and action items
- radar category/status

Behavior:

- if explicit score fields are provided during ingest, they are stored
- otherwise fallback scoring is computed automatically during ingest
- legacy rows without stored scores still return computed fallback scores through the API

This prepares the project for later Telegram filtering and richer web ranking without breaking existing issue data.

## Phase 4 telegram-ready delivery layer

Telegram transport itself is still outside this repository, but the repo now exposes a Telegram-ready delivery layer:

- score threshold decision logic
- important-item threshold logic
- formatted Telegram preview text
- delivery preview API per article
- delivery log recording API for external senders such as OpenClaw

Current behavior:

- repo decides whether an article should be sent based on `final_score`
- repo formats the message body that an external sender can reuse
- repo can record send results back onto the article record

Relevant backend settings:

- `TECH_RADAR_MIN_TELEGRAM_SCORE` (default `7.0`)
- `TECH_RADAR_IMPORTANT_SCORE` (default `8.5`)

New delivery endpoints:

- `GET /api/issues/{slug}/delivery-preview`
- `POST /api/issues/{slug}/delivery-log`

This keeps Telegram transport concerns separate from analysis/storage logic while still making the output channel-ready.

## Ingestion flow

### Publish prepared markdown from stdin

```bash
cat article.md | python scripts/geeknews_publish.py
```

### Direct ingest payload

`ingest_issue.py` uses the same backend settings as the FastAPI app, so it writes to the canonical `DATABASE_URL` target and `CONTENT_ROOT` path from `backend/.env`.

`ingest_issue.py` expects JSON on stdin with:

- `issue_date`
- `title`
- `summary`
- `markdown`
- optional `short_summary`
- optional `impact_summary`
- optional `action_items`
- optional `tags`
- optional `radar_category`
- optional `radar_status`
- optional score fields (`interest_score`, `project_score`, `novelty_score`, `actionability_score`, `credibility_score`, `community_score`, `final_score`, `score_reason`, `recommended_action`)
- optional `slug`

## API

- `GET /api/issues`
- `GET /api/issues/latest`
- `GET /api/issues/{slug}`
- `GET /api/issues/{slug}/delivery-preview`
- `POST /api/issues/{slug}/delivery-log`
- `POST /api/issues/ingest`

## Tests

Backend tests currently include profile loader coverage.

```bash
cd backend
source .venv/bin/activate
pytest
```

## Operations helper

For backend restart and smoke-checks, use:

```bash
./scripts/restart_backend.sh
```

What it does:
- stops the user backend service
- clears listeners on port `8010`
- restarts `technews-backend.service`
- checks `/health` and `/openapi.json`
- prints recent logs on failure
- attempts one direct `uvicorn` run to surface a traceback when startup still fails

For frontend production restart and smoke-checks, use:

```bash
./scripts/restart_frontend.sh
```

Additional operational references:

- deployment notes: `deploy/README.md`
- score design notes: `docs/scoring-notes.md`
- backup and restore: `BACKUP_RESTORE.md`

## Recovery notes

If you need to rebuild the repo checkout and restore service state, the most important files to preserve are:

- `backend/.env`
- `backend/technews.db`
- private profile file referenced by `TECH_RADAR_PROFILE_PATH`

Operational files outside the repo may also matter:

- `~/.config/systemd/user/technews-backend.service`
- `~/.config/systemd/user/technews-frontend.service`
- active nginx site config that routes `/technews/` and `/technews-api/`

Use `BACKUP_RESTORE.md` for a step-by-step recovery flow.

What it does:
- stops the user frontend service if present
- clears listeners on port `3012`
- removes stale production build output
- rebuilds the frontend in a production-only dist dir
- verifies production build artifacts like `.next-prod/BUILD_ID`
- starts `next start` on `127.0.0.1:3012`
- checks `/technews/` over HTTP

Recommended rule:
- do not mix ad-hoc `next dev` / `next start` processes with the production frontend port
- keep dev and prod build outputs separate, dev in `.next`, prod in `.next-prod`
- when the frontend looks stale or returns `502`, prefer `./scripts/restart_frontend.sh`
- treat a build as valid only if the build command succeeds **and** `.next-prod/BUILD_ID` exists

## Notes

- Canonical SQLite DB path is the project root file `technews.db` unless `DATABASE_URL` overrides it.
- Canonical markdown content root is the workspace-level `../content` path unless `CONTENT_ROOT` overrides it.
- CLI ingest and FastAPI ingest should always point at the same DB and content root.
- Telegram sending is not implemented inside this repository today.
- This repository currently focuses on storage and web publishing.
- Future phases can build scoring, matching, delivery logs, and trend analysis on top of the current issue pipeline.
