# FINAL-L5-00 — Artifact Retention Policy

## .gitignore review
`.gitignore` did not exist before this sprint. It now covers:
- `node_modules/`, `.next/`, `dist/`, `build/`, `coverage/` — standard JS build/dep output
- `__pycache__/`, `*.pyc`, `.pytest_cache/`, `.mypy_cache/`, `.ruff_cache/`, `venv/`, `.venv/` — Python build/cache output
- `.env`, `.env.local`, `.env.*.local`, `.env.production` — secrets (`.env.example` files remain tracked as templates)
- `*.log` — all logs, repo-wide
- `test-results/`, `playwright-report/`, `blob-report/`, `playwright/.cache/` — Playwright transient output
- `.DS_Store`, `Thumbs.db`, `.vscode/`, `.idea/`, `.claude/` — OS/IDE/tool metadata
- `uploads/` — runtime user-uploaded data
- `db/pgsql/`, `db/pgdata/`, `db/*.zip`, `db/pgvector_extract/` — bundled local Postgres/pgAdmin install and live data (see Part 2 finding)

## Retention decisions

1. **E2E reports**: Not committed as generated HTML/JSON reports — `playwright-report/` and `test-results/` are gitignored. The narrative `.md` certification reports at repo root (e.g. `ADMIN_TENANT_E2E_*_REPORT.md`) ARE committed and ARE the intended durable record of E2E runs — they are hand/AI-authored summaries, not raw Playwright output, so this is a deliberate distinction: raw tool output = ignored, written evidence = kept.
2. **Screenshots**: No committed screenshot directories were found during the inventory scan. If Playwright screenshot output exists locally it falls under `test-results/`, already ignored.
3. **Traces/videos**: Playwright traces/videos are transient by nature and covered under `test-results/`/`playwright-report/` — never intended for git.
4. **Final certification evidence**: The 10 Sprint-36 `docs/*FINAL*.md` proof documents and the root `TEST_RESULTS.md`/`REMAINING_BLOCKERS.md` are retained as committed, durable evidence per the Document Cleanup Manifest (KEEP_REFERENCE / KEEP_CURRENT).
5. **Local logs**: All `*.log` files, wherever created, are ignored — logs are debug output, not evidence; if a log needs to be preserved as evidence it should be renamed/moved into a report `.md` or an explicit evidence folder, not left as a loose `.log`.

## Policy going forward
- Anyone starting a local dev/backend/frontend server should expect their `*.log` output to never be committed — this is now enforced by `.gitignore`, not just convention.
- The `db/` bundled Postgres install should not be reintroduced to git under any filename; if the team wants a documented "how to set up local Postgres" step, that belongs in a setup doc, not a committed binary bundle.
