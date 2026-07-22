# Startup and Health Integrity Guard Decision

## Decision: standalone scheduled command, NOT wired into application startup

## Reasoning
- **Production startup should not expose sensitive account information** — satisfied by design: the new `scripts/workflow_rearchitecture/check_role_integrity.py` prints only a count by default; account-level detail (email, role, active status — never password/token data) requires an explicit `--detail` flag, an opt-in an operator chooses when they've already decided to investigate.
- **Must not silently repair records** — confirmed: the script is purely read-only (a single `SELECT count(*)`, optionally a second `SELECT` for detail); it contains no `UPDATE`/`INSERT`/`DELETE` statement anywhere.
- **Must not block the entire platform unless policy requires it** — this is exactly why it's a standalone script, not startup middleware: a demo/dev database with 1 known invalid account (as this repository currently has) would otherwise prevent the entire application from booting, which is a worse failure mode than a visible, actionable integrity signal.
- **Operational administrators should receive a clear integrity finding** — the script's exit code (0 = clean, 1 = violation found) makes it directly usable as a CI gate or cron-triggered alert, and its JSON output (`{"invalid_role_count": N, "status": "..."}`) is machine-parseable for a monitoring pipeline.

## What was NOT done
No change was made to `app/main.py` or any startup/health-check endpoint. This codebase's existing health-check architecture was not independently investigated for whether a lightweight, count-only version of this check would fit naturally into an existing `/health` or `/ready` endpoint — that would be a reasonable follow-up but was not pursued this slice to avoid touching production-facing endpoints without a full understanding of their existing contract and consumers (out of this slice's bounded, tenant-access-model-focused scope).

## Recommended operational usage
Run `python scripts/workflow_rearchitecture/check_role_integrity.py` on a schedule (daily cron, or as a CI step against a staging database) and alert on non-zero exit code. This closes the loop on Migration 144's own detection logic by giving operators a lightweight way to check for drift *before* attempting the migration, without needing to run alembic itself to find out.
