# FINAL-L5-01 — Database Backup Report

| Field | Value |
|---|---|
| Environment | Local development (`APP_ENV=development`, confirmed loopback host) |
| Database target | `127.0.0.1:5432/serviceos` |
| Backup type | Full custom-format dump (`pg_dump -F c`) + schema-only SQL dump |
| Backup path | `.backups/final-l5-01/serviceos_pre_reset_20260711-001711.dump` (full), `.backups/final-l5-01/serviceos_schema_only_20260711-001711.sql` (schema-only) |
| Backup time | 2026-07-11 00:17:11 local |
| Migration head at backup time | `131 (head)` |
| Dump size | 1,958,406 bytes (~1.9 MB) |
| Restore command | `"db/pgsql/bin/pg_restore.exe" -h 127.0.0.1 -p 5432 -U <user> -d serviceos --clean --if-exists ".backups/final-l5-01/serviceos_pre_reset_20260711-001711.dump"` |
| Verification result | `pg_dump` exited 0; `pg_restore --list` against the dump file succeeded and enumerated 2,176 restorable objects (tables, indexes, constraints, data) — confirms the dump is structurally valid and restorable without needing to perform a full restore-and-diff |

Dump files are stored under `.backups/final-l5-01/`, which is excluded from git via `.gitignore` (added this sprint) — they will never be committed, since they may contain real names/emails/data even in a dev database.

**Result: Backup succeeded.** Not a blocker.
