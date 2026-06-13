# FamilyHub production image.
#
# TEACHING NOTE (this is the Docker from D387's stack, met early): an
# image is a frozen, reproducible machine — same Python, same packages,
# same code — so "works on my machine" becomes "works in the image",
# everywhere. Build once, run identically on the Windows desktop, the
# Fedora ThinkPad, and Lightsail.
#
#   docker compose up --build      (see docker-compose.yml)

# slim = Debian with just enough to run Python. Pillow and pillow-heif
# ship pre-built "wheels" for this platform, so no compilers needed.
FROM python:3.14-slim

WORKDIR /app

# Dependencies FIRST, code second — Docker caches each step, and
# requirements change far less often than code. Ordering it this way
# means a code-only change rebuilds in seconds, not minutes.
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Never run as root inside a container: if the app is ever compromised,
# the blast radius is one unprivileged user, not the container's root.
# (chmod +x on the entrypoint here too — git on Windows can lose the
# executable bit, and a non-executable entrypoint is a dead container.)
RUN useradd --create-home familyhub \
    && mkdir -p instance uploads backups export \
    && chmod +x scripts/docker-entrypoint.sh \
    && chown -R familyhub:familyhub /app
USER familyhub

EXPOSE 8000

# The entrypoint applies database migrations, THEN starts gunicorn —
# a fresh container always boots with a current schema.
ENTRYPOINT ["./scripts/docker-entrypoint.sh"]
