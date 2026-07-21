# Environment Readiness — Round 2 (Workstream 1/2)

## Infrastructure availability (recorded this round)

- Backend: `http://localhost:8000/health` -> `status:"ok"`, 35 engines healthy, postgres ok (2.9ms), redis ok (1.0ms).
- Database: reachable directly via `asyncpg` from the Windows host (`localhost:5432`, `serviceos`/`serviceos`) — used for a targeted `service_pricing_rules`/`service_types` lookup in Round 1 and attempted again this round (a follow-up query against `master_services`/`bargain_rules` failed with `UndefinedColumnError` — real schema-naming mismatch in my ad hoc query, not a DB outage; the API-level checks below were used instead and succeeded).
- WSL: `wsl --list` -> Debian (default) available. `node --version` -> v20.20.2, `npm --version` -> 10.8.2, `python3 --version` -> Python 3.13.5, user `admin` (not `root` as prior-phase docs assumed — noted as a real, minor environment difference from what earlier UX-phase docs described; did not block any work this round).
- Native Windows npm install: NOT re-attempted, per this round's brief and prior UX-01–06 findings (`ERR_SSL_CIPHER_OPERATION_FAILED`, proven unfixable across dozens of attempts) — WSL used exclusively, as instructed.
- Playwright/Chromium: NOT installed/verified this round (see `playwright-baseline.md` for the explicit deferral reason).
- Stale processes observed in the persistent WSL instance (`next dev` on 3000/3001 under a different user, `expo start --web` on 19006) were checked and found NOT actually listening (connection refused on all 3 ports) — leftover zombie processes from an earlier session, not relied upon for any evidence this round.

## Round 1 evidence preserved (re-verified this round)

- Booking `BK-20260721-000008` / job `JOB-20260721-000008` still exists, still `status:"accepted"` (re-fetched live via `GET /v1/customer/bookings/9fb8900f-...`).
- `real-record-evidence.csv`, `live-e2e-evidence.md`, and all other Round 1 docs are untouched (only new Round-2 files added or explicit "Round 2:" sections appended to shared files, per the coordinator's instruction).
- `mobile/customer-app/src/lib/chatLanguages.ts` still contains exactly the 3-language (`en`/`hi`/`pa`) registry from Round 1; sole consumer still `DeepSeekChatScreen.tsx` (re-confirmed via grep).
- Ancestry re-verified: `git merge-base --is-ancestor` for `7488335`/`493a132`/`b426e08` against `HEAD` all return true (checked at both the start of Round 2 and again before this doc was written).
