# TechNews Publisher deployment notes

## Reverse proxy layout

TechNews Publisher is served behind nginx with two paths:

- `/technews/` → Next.js frontend
- `/technews-api/` → FastAPI backend

## Important routing detail

The frontend is now served as a **root-path Next.js app**.
That means `next.config.ts` does **not** use `basePath`.

Because of that, nginx must do two things:

1. Forward `/technews/` requests to the frontend app root
2. Forward `/_next/` asset requests to the same frontend process

Without the `/_next/` proxy block, the page HTML may load while JS/CSS assets fail with 404 or 400 errors.

## Working nginx example

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

location /technews/ {
  proxy_pass http://127.0.0.1:3013/;
  proxy_http_version 1.1;
  proxy_set_header Host $host;
  proxy_set_header X-Real-IP $remote_addr;
  proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
  proxy_set_header X-Forwarded-Proto $scheme;
  proxy_set_header Upgrade $http_upgrade;
  proxy_set_header Connection "upgrade";
}

location /_next/ {
  proxy_pass http://127.0.0.1:3013/_next/;
  proxy_http_version 1.1;
  proxy_set_header Host $host;
  proxy_set_header X-Real-IP $remote_addr;
  proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
  proxy_set_header X-Forwarded-Proto $scheme;
  proxy_set_header Upgrade $http_upgrade;
  proxy_set_header Connection "upgrade";
}
```

## Why this setup was needed

Previous attempts mixed these two approaches:

- Next.js `basePath: '/technews'`
- nginx prefix proxying `/technews/`

That caused stale chunk paths, missing assets, and mobile hard-refresh failures.

The stable approach is:

- keep Next.js at root path
- let nginx own the `/technews` prefix
- proxy `/_next/` explicitly

## Verification checklist

After deploy, verify all three:

1. Page HTML loads
   - `GET /technews/` → 200
2. Frontend assets load
   - `GET /_next/static/...` → 200
3. API works
   - `GET /technews-api/api/issues/latest` → 200

If the page opens but the browser console shows chunk or CSS load failures, check whether nginx is forwarding `/_next/` to the same frontend process that served `/technews/`.
