#!/usr/bin/env bash
# ServiceOS — Background Job Cron Reference
#
# Copy relevant lines into your crontab or task scheduler.
# All jobs are idempotent and safe to run more frequently.
# Run from the repo root with the virtualenv activated.
#
# Usage: crontab -e  (then paste the lines below)
# Or:    docker exec serviceos_api python -m app.jobs.notifications dispatch

# ── Notification dispatch (every 1 minute) ────────────────────────────────────
* * * * * cd /srv/serviceos && /venv/bin/python -m app.jobs.notifications dispatch >> /var/log/serviceos/notif_dispatch.log 2>&1

# ── Notification retry (every 5 minutes) ──────────────────────────────────────
*/5 * * * * cd /srv/serviceos && /venv/bin/python -m app.jobs.notifications retry >> /var/log/serviceos/notif_retry.log 2>&1

# ── Notification cleanup (hourly) ─────────────────────────────────────────────
0 * * * * cd /srv/serviceos && /venv/bin/python -m app.jobs.notifications cleanup >> /var/log/serviceos/notif_cleanup.log 2>&1

# ── Draft / slot-hold expiry (every 15 minutes) ───────────────────────────────
*/15 * * * * cd /srv/serviceos && /venv/bin/python -m app.jobs.expire_drafts >> /var/log/serviceos/expire_drafts.log 2>&1
