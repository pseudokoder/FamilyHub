# Deploying FamilyHub to Lightsail (Ubuntu)

The repeatable recipe. Everything here was previously prose in DEVDIARY
Chapter 8 — now it's files you copy into place.

## One-time setup

```bash
# 1. Code + Python
sudo apt update && sudo apt install -y python3-venv nginx
git clone https://github.com/pseudokoder/FamilyHub.git ~/FamilyHub
cd ~/FamilyHub && python3 -m venv .venv
.venv/bin/pip install -r requirements.txt

# 2. Secrets — copy .env.example to .env and set for production:
#    SECRET_KEY (long + random), SESSION_COOKIE_SECURE=True,
#    TRUST_PROXY=True, BACKUP_S3_BUCKET + AWS keys, MAIL_* (optional)
cp .env.example .env && nano .env

# 3. Database + first admin
.venv/bin/flask db upgrade
.venv/bin/flask create-admin wes

# 4. gunicorn under systemd
sudo cp scripts/deploy/familyhub.service /etc/systemd/system/
sudo systemctl daemon-reload && sudo systemctl enable --now familyhub

# 5. nginx in front
sudo cp scripts/deploy/nginx.conf /etc/nginx/sites-available/familyhub
sudo ln -s /etc/nginx/sites-available/familyhub /etc/nginx/sites-enabled/
sudo nginx -t && sudo systemctl reload nginx

# 6. HTTPS (also flips on the app's HSTS header)
sudo apt install -y certbot python3-certbot-nginx
sudo certbot --nginx -d familyhub.pseudokoder.com

# 7. Nightly verified backup (3:15 AM, logged, off-site if bucket set)
crontab -e   # add:
# 15 3 * * * cd /home/ubuntu/FamilyHub && .venv/bin/flask backup >> backups/backup.log 2>&1
```

## Sanity checks after deploy

- `curl -s https://familyhub.pseudokoder.com/health` → `{"status":"ok",...}`
- Padlock in the browser; `Strict-Transport-Security` header present
- Next morning: `tail backups/backup.log` shows a verified backup

## Updating the running site

```bash
cd ~/FamilyHub && git pull
.venv/bin/pip install -r requirements.txt
.venv/bin/flask db upgrade
sudo systemctl restart familyhub
```
