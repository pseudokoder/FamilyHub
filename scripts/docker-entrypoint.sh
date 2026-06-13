#!/bin/sh
# Container startup: migrate, then serve.
#
# `flask db upgrade` is idempotent — it applies only migrations the
# database hasn't seen, so running it on EVERY boot is safe and means a
# freshly pulled image can never run against a stale schema.
#
# `exec` replaces this shell with gunicorn so signals (docker stop's
# SIGTERM) reach the server directly — graceful shutdowns, not kills.
#
# Workers=2: right-sized for family traffic on a small Lightsail box.
# (Note from DEVDIARY Ch. 12: the login rate limiter counts per worker
# with memory:// storage — 2 workers means the practical login budget is
# up to 20/min/IP. Still robot-proof; swap in Redis storage if workers
# ever multiply.)
set -e

flask db upgrade
exec gunicorn --bind 0.0.0.0:8000 --workers 2 --access-logfile - "run:app"
