# Personal Tech Radar deployment notes

This document describes the current production-style deployment shape used by this repo.

## Runtime layout

Personal Tech Radar is served behind nginx with these public paths:

- `/technews/` -> Next.js frontend
- `/technews-api/` -> FastAPI backend

Local process ports:

- frontend: `127.0.0.1:3012`
- backend: `127.0.0.1:8010`

User systemd units:

- `technews-frontend.service`
- `technews-backend.service`

## Current frontend deployment model

The frontend is a root-path Next.js app that is exposed by nginx under the `/technews` prefix.

Current production flow is:

1. build frontend into `frontend/.next-prod`
2. publish static assets from `frontend/.next-prod/static/`
3. rsync them into `/var/www/technews-next-static`
4. run the Next.js server on `127.0.0.1:3012`
5. let nginx proxy `/technews/` to that server
6. let nginx serve `/technews/_next/static/` directly from `/var/www/technews-next-static`

This is different from the earlier pure `/_next/` proxy approach.

## Current helper scripts

### Backend

```bash
./scripts/restart_backend.sh
```

What it does:

- stops `technews-backend.service`
- clears listeners on port `8010`
- starts the user service again
- checks `/health`
- checks `/openapi.json`
- prints issue-related route names as a smoke test

### Frontend

```bash
./scripts/restart_frontend.sh
```

What it does:

- stops `technews-frontend.service`
- clears listeners on port `3012`
- removes old `frontend/.next-prod`
- runs `npm run build:prod:app`
- publishes static files through `scripts/publish_frontend_static.sh`
- starts the user service again
- checks `http://127.0.0.1:3012/technews/`

### Static asset publish

```bash
./scripts/publish_frontend_static.sh
```

What it does:

- reads from `frontend/.next-prod/static/`
- syncs to `/var/www/technews-next-static`

## nginx expectations

The active nginx config should do all of the following:

1. redirect `/technews` to `/technews/`
2. proxy `/technews/` to `127.0.0.1:3012`
3. proxy `/technews-api/` to `127.0.0.1:8010`
4. serve `/technews/_next/static/` from `/var/www/technews-next-static`

Example shape:

```nginx
location /technews-api/ {
  proxy_pass http://127.0.0.1:8010/;
  proxy_http_version 1.1;
  proxy_set_header Host $host;
  proxy_set_header X-Real-IP $remote_addr;
  proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
  proxy_set_header X-Forwarded-Proto $scheme;
}

location = /technews {
  return 301 /technews/;
}

location ^~ /technews/_next/static/ {
  alias /var/www/technews-next-static/;
  access_log off;
  expires 1y;
  add_header Cache-Control "public, max-age=31536000, immutable";
}

location /technews/ {
  proxy_pass http://127.0.0.1:3012;
  proxy_http_version 1.1;
  proxy_set_header Host 127.0.0.1:3012;
  proxy_set_header X-Forwarded-Host $host;
  proxy_set_header X-Real-IP $remote_addr;
  proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
  proxy_set_header X-Forwarded-Proto $scheme;
  proxy_set_header Upgrade $http_upgrade;
  proxy_set_header Connection "upgrade";
}
```

## Verification checklist

After deploy, verify all of these:

1. backend health
   - `curl http://127.0.0.1:8010/health`
2. frontend local response
   - `curl -I http://127.0.0.1:3012/technews/`
3. public frontend
   - Set `PUBLIC_BASE_URL` in the local shell to the public origin without a trailing slash.
   - `curl -I "${PUBLIC_BASE_URL:?Set PUBLIC_BASE_URL before running this check}/technews/"`
4. public API
   - `curl -I "${PUBLIC_BASE_URL:?Set PUBLIC_BASE_URL before running this check}/technews-api/api/issues/latest"`
5. static asset directory exists
   - `ls /var/www/technews-next-static`

The public checks intentionally read `PUBLIC_BASE_URL` from the operator's local
environment instead of storing a personal hostname in this repository.

## Common failure modes

If page HTML loads but styling or client-side JS is broken:

- check whether `frontend/.next-prod/static/` was built
- check whether `/var/www/technews-next-static` was updated
- check nginx `location ^~ /technews/_next/static/`

If backend restart script fails unexpectedly:

- read recent user journal for `technews-backend.service`
- check whether another process is still holding `127.0.0.1:8010`
- note that the fallback direct uvicorn traceback helper can collide if the service already recovered during the script
