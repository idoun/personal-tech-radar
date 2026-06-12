# Personal Tech Radar Backup and Restore Guide

This guide is for the case where you remove the current repo checkout, clone it again, and restore the service with minimal surprises.

## 1. What to back up

Required:

- `backend/.env`
- `backend/technews.db`
- private profile file referenced by `TECH_RADAR_PROFILE_PATH`

Important if you want the deployed service to come back the same way:

- `~/.config/systemd/user/technews-backend.service`
- `~/.config/systemd/user/technews-frontend.service`
- active nginx site config that contains `/technews` and `/technews-api` routing

Important for frontend static serving:

- `/var/www/technews-next-static`

Usually not needed because it is regenerated:

- `frontend/.next-prod`
- `frontend/node_modules`
- `backend/.venv`

## 2. Recommended backup folder

Use a dated folder outside the repo.

Example:

```bash
mkdir -p ~/backups/technews-publisher-2026-06-12
```

## 3. Copy the files into backup

From the repo root:

```bash
cp backend/.env ~/backups/technews-publisher-2026-06-12/
cp backend/technews.db ~/backups/technews-publisher-2026-06-12/
cp /home/ubuntu/.config/technews/tech-radar-profile.yaml ~/backups/technews-publisher-2026-06-12/
cp ~/.config/systemd/user/technews-backend.service ~/backups/technews-publisher-2026-06-12/
cp ~/.config/systemd/user/technews-frontend.service ~/backups/technews-publisher-2026-06-12/
sudo cp /etc/nginx/sites-available/idounaichat ~/backups/technews-publisher-2026-06-12/
sudo cp -r /var/www/technews-next-static ~/backups/technews-publisher-2026-06-12/
```

If the nginx config lives under a different filename, back up that real active file instead.

## 4. Delete and clone again

Safer example:

```bash
cd /home/ubuntu/.openclaw/workspace
mv technews-publisher technews-publisher.old
git clone <repo-url> technews-publisher
cd technews-publisher
```

Using `mv` is safer than deleting immediately.

## 5. Restore the backed up files

Assuming backup folder `~/backups/technews-publisher-2026-06-12`:

```bash
cp ~/backups/technews-publisher-2026-06-12/.env backend/.env
cp ~/backups/technews-publisher-2026-06-12/technews.db backend/technews.db
mkdir -p /home/ubuntu/.config/technews
cp ~/backups/technews-publisher-2026-06-12/tech-radar-profile.yaml /home/ubuntu/.config/technews/tech-radar-profile.yaml
cp ~/backups/technews-publisher-2026-06-12/technews-backend.service ~/.config/systemd/user/
cp ~/backups/technews-publisher-2026-06-12/technews-frontend.service ~/.config/systemd/user/
sudo cp ~/backups/technews-publisher-2026-06-12/idounaichat /etc/nginx/sites-available/idounaichat
sudo rsync -a ~/backups/technews-publisher-2026-06-12/technews-next-static/ /var/www/technews-next-static/
```

## 6. Reinstall runtime dependencies

Backend:

```bash
cd /home/ubuntu/.openclaw/workspace/technews-publisher/backend
python3 -m venv .venv
. .venv/bin/activate
pip install -r requirements.txt
```

Frontend:

```bash
cd /home/ubuntu/.openclaw/workspace/technews-publisher/frontend
npm install
```

## 7. Rebuild and restart

Preferred production-style recovery:

```bash
cd /home/ubuntu/.openclaw/workspace/technews-publisher
./scripts/restart_backend.sh
./scripts/restart_frontend.sh
systemctl --user daemon-reload
sudo nginx -t
sudo systemctl reload nginx
```

If service files changed, run `systemctl --user daemon-reload` before restarting.

## 8. Verify

Backend:

```bash
curl http://127.0.0.1:8010/health
curl http://127.0.0.1:8010/openapi.json | jq '.paths | keys[]' | grep issues
```

Frontend local:

```bash
curl -I http://127.0.0.1:3012/technews/
```

Public:

```bash
curl -I https://idoun.pe.kr/technews/
curl -I https://idoun.pe.kr/technews-api/api/issues/latest
```

## 9. Minimum safe recovery set

If you only want the smallest restore set that matters most:

1. `backend/.env`
2. `backend/technews.db`
3. private profile file referenced by `TECH_RADAR_PROFILE_PATH`
4. `~/.config/systemd/user/technews-backend.service`
5. `~/.config/systemd/user/technews-frontend.service`
6. active nginx site config

Everything else can be rebuilt or republished from those pieces.
