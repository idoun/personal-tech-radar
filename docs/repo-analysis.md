# TechNews Publisher repository analysis

> Historical note: this document was written as an early repository snapshot.
> Parts of it no longer match the current production implementation exactly.
> For current behavior, prefer `README.md`, `docs/scoring-notes.md`, and deployment/recovery guides.

## Overview

This repository is a lightweight GeekNews publishing stack with a split architecture:

- **Backend**: FastAPI + SQLAlchemy + SQLite
- **Frontend**: Next.js App Router + React
- **Ingestion scripts**: small Python CLI scripts writing markdown content plus DB rows
- **Deployment**: nginx reverse proxy plus user systemd services

Current implemented product scope is narrower than the target Personal Tech Radar Agent.
Right now it behaves like a daily GeekNews archive publisher rather than a personalized scoring/radar system.

## Repository structure

```text
technews-publisher/
├── backend/
│   ├── app/
│   │   ├── api/routes_issues.py
│   │   ├── core/config.py
│   │   ├── db/session.py
│   │   ├── models/issue.py
│   │   ├── schemas/issue.py
│   │   └── main.py
│   ├── requirements.txt
│   └── .env(.example)
├── frontend/
│   ├── app/
│   ├── components/technews-shell.tsx
│   ├── lib/api.ts
│   ├── lib/types.ts
│   ├── next.config.ts
│   └── package.json
├── scripts/
│   ├── ingest_issue.py
│   └── geeknews_publish.py
├── deploy/
│   └── README.md
├── .runtime/
│   ├── technews-backend.service
│   └── technews-frontend.service
└── technews.db
```

## Languages, frameworks, package managers

### Backend
- **Language**: Python
- **Framework**: FastAPI
- **ORM**: SQLAlchemy
- **Validation/config**: Pydantic, pydantic-settings
- **Package manager style**: `pip` with `requirements.txt`
- **Database**: SQLite

### Frontend
- **Language**: TypeScript
- **Framework**: Next.js 15 App Router
- **UI**: React 19
- **Markdown rendering**: react-markdown + remark-gfm
- **Package manager style**: npm with `package-lock.json`

## Current runtime architecture

### Data flow

1. A separate external GeekNews summarization flow appears to generate markdown.
2. `scripts/geeknews_publish.py` derives issue metadata such as title/date/summary.
3. `scripts/ingest_issue.py` writes:
   - rendered markdown file into workspace-level `content/YYYY/MM/...`
   - matching row into SQLite `issues` table
4. FastAPI exposes published issues through `/api/issues` endpoints.
5. Next.js frontend fetches those endpoints and renders archive/detail views.
6. nginx exposes frontend under `/technews` and backend under `/technews-api`.

## Existing feature map

### 1. Collection / ingestion
Current repo does **not** contain a full crawler for hada.io inside this repository.
Instead, it contains the last-mile ingest/publish step:

- `scripts/geeknews_publish.py`
  - reads markdown from stdin
  - derives issue date and summary
  - calls local ingest logic
- `scripts/ingest_issue.py`
  - writes markdown file to content storage
  - upserts the `issues` SQLite row

This means the upstream fetch/summarize/Telegram source pipeline likely exists outside this repo or is invoked elsewhere.

### 2. Summary storage
This section is outdated.

The current implementation already stores and exposes structured summary and score-related fields, including:

- `short_summary`
- `impact_summary`
- `action_items`
- `tags`
- `radar_category`
- `radar_status`
- score breakdown fields
- delivery-oriented metadata

### 3. Telegram logic
There is still no direct Telegram transport inside this repository, but this section is also partially outdated.

The repo now contains Telegram-oriented delivery preparation such as:

- delivery preview formatting
- score threshold decisions
- delivery log recording endpoints

### 4. Web publishing
The frontend is a single-page archive/detail experience:

- left archive list grouped by month
- right detail panel with top summary and parsed markdown cards
- API calls:
  - `GET /api/issues`
  - `GET /api/issues/latest`
  - `GET /api/issues/:slug`

### 5. Database usage
Current DB is SQLite with a single core domain table:

- `issues`

The SQLAlchemy model includes:
- slug
- title
- summary
- issue_date
- year/month
- markdown_path
- is_published
- created_at / updated_at

This is a good minimal base for incremental expansion.

## Important files

### Backend
- `backend/app/core/config.py`
  - environment-driven settings
  - currently supports app name/env, DB URL, content root, ingest token
- `backend/app/api/routes_issues.py`
  - main issue listing/detail/ingest API
- `backend/app/models/issue.py`
  - current persistence model
- `backend/app/schemas/issue.py`
  - API schemas

### Scripts
- `scripts/geeknews_publish.py`
  - issue title/date/summary derivation helper
- `scripts/ingest_issue.py`
  - direct DB + markdown writer

### Frontend
- `frontend/components/technews-shell.tsx`
  - main archive/detail UI
- `frontend/lib/api.ts`
  - frontend API access
- `frontend/next.config.ts`
  - currently configured for `/technews` deployment

## Environment/config structure

### Backend env
From `backend/app/core/config.py`, current env settings are:
- `app_name`
- `app_env`
- `database_url`
- `content_root`
- `ingest_token`

### Frontend env
From `frontend/lib/api.ts`, frontend can use:
- `NEXT_PUBLIC_API_BASE_URL`

By default it uses same-origin `/technews-api` in browser and `http://127.0.0.1:8010` on server.

## Execution and deployment clues

### Backend
Likely run via uvicorn, either directly or user systemd.

### Frontend
Run via:
- `npm run build`
- `npm run start`

Systemd service files under `.runtime/` indicate intended long-running deployment.

## What already matches the Personal Tech Radar direction

Useful existing foundations:
- a stable issue ingestion entrypoint
- markdown + DB split storage
- frontend archive UI already rendering issue detail pages
- SQLite persistence that can be extended incrementally
- FastAPI API surface that can grow without a rewrite

## Current gaps versus target roadmap

This list is stale and should not be treated as a current roadmap gap list.

Some items below were already implemented after this note was written:

- personal interest/project profile config
- structured summary fields
- score breakdowns
- project matching
- delivery logs
- tests

Items still better treated as future work include:

- deeper trend/radar/search APIs
- richer evaluation/observability around scoring quality
- broader operational recovery documentation

## Recommended Phase 1 implementation strategy

To preserve the existing structure, Phase 1 should:

1. Add a **config-backed profile file** rather than redesigning current issue flow.
2. Implement a small **profile loader** in backend code first, since backend settings already exist.
3. Provide a safe default profile when file/config is missing.
4. Keep profile loading isolated from current publish/display logic so existing behavior does not break.
5. Add tests around profile parsing and fallback behavior.
6. Update project documentation with profile configuration and environment variable usage.

## Proposed minimal Phase 1 integration points

- Add `config/tech-radar-profile.yaml`
- Add backend module such as `backend/app/core/profile.py`
- Extend settings with `tech_radar_profile_path`
- Keep the profile unused by current issue API for now except as loadable infrastructure
- Add unit tests for:
  - explicit profile file
  - missing profile file fallback
  - malformed profile handling strategy

## Risk notes

- There is both SQLAlchemy API ingestion and direct sqlite script ingestion. Future phases should avoid duplicating schema logic further.
- Telegram behavior is currently outside the repo, so later Telegram-related work may require either importing upstream logic or moving sending into this repo.
- Deployment has recently been fragile around `/technews` path hosting, so frontend changes should stay incremental.
