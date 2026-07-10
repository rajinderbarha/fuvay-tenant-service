# Data Reset — Environment Safety Check

| Item | Value |
|---|---|
| **Current environment name** | `development` (`APP_ENV=development` in `.env`; `app/config.py:27` default is also `"development"`) |
| **Database host/name** | `127.0.0.1:5432/serviceos` (local Postgres, not a remote/managed host) |
| **App mode** | `app/config.py:147` — `is_development` property confirms `APP_ENV == "development"` |
| **Cleanup allowed** | **YES** — matches the explicit safe-list (`local`/`development`/`dev`) |
| **Reason** | `DATABASE_URL` points at `127.0.0.1` (loopback, not a cloud/managed DB host), `APP_ENV=development`, no `staging-live`/`production`/`live` markers found anywhere in `.env` or `.env.local` |
| **Timestamp** | 2026-07-08 (session date) |
| **Command used** | Manual environment inspection: `grep APP_ENV/DATABASE_URL .env`, `app/config.py` literal type check — no destructive command has been run yet at time of writing this file |
| **Safety guard implementation** | See below |

## Safety guard implementation

Before this sprint, **no dedicated reset script existed** (`scripts/serviceos_reset_dev_data.py` did not exist; no `npm run serviceos:reset-dev-data` script was defined in `frontend/super-admin/package.json`). Both were required to be created or verified per this ticket.

The new script `scripts/serviceos_reset_dev_data.py` (created this sprint) enforces the guard **in code**, not just by convention:

```python
ALLOWED_ENVIRONMENTS = {"local", "development", "dev", "test", "staging-test", "certification"}
FORBIDDEN_ENVIRONMENTS = {"production", "prod", "staging-live", "live"}

env = os.getenv("APP_ENV", "development").lower()
db_url = os.getenv("DATABASE_URL", "")

if env in FORBIDDEN_ENVIRONMENTS:
    print(f"[REFUSED] APP_ENV={env} is forbidden for data reset. Aborting.")
    sys.exit(1)
if env not in ALLOWED_ENVIRONMENTS:
    print(f"[REFUSED] APP_ENV={env} is not in the explicit allow-list. Aborting.")
    sys.exit(1)
if any(host in db_url for host in (".amazonaws.com", ".azure.com", ".gcp.com", "prod-")):
    print(f"[REFUSED] DATABASE_URL host looks like a managed/cloud/production host. Aborting.")
    sys.exit(1)
```

The script additionally requires an explicit `--confirm` flag and prints a full dry-run summary (row counts per table) before any deletion, refusing to proceed without it.

## Decision point

**This sprint stops here, before running any destructive statement, pending explicit user confirmation of the cleanup scope.**

Rationale (see `DATA_CLEANUP_AUDIT.md` for full detail): although the environment
is confirmed safe (`development`, local DB), this database contains
substantial seeded/built-up state from ~20+ prior certification sprints in
this same project (tenants, customers, bookings, catalog mappings, dashboard
command center data, DPDP compliance requests, etc.), and independent
evidence exists of a concurrent process also actively reading/writing this
same database throughout this session. A mass truncation across 20+ tables
is a hard-to-reverse action with a blast radius large enough to warrant an
explicit go-ahead before executing, even in a confirmed-safe environment —
per this project's standing operating rule to pause before irreversible,
wide-blast-radius actions rather than proceed on ticket text alone.
