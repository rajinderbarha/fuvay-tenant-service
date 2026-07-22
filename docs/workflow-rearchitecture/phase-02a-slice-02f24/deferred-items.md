# Deferred Items — Slice 2F-24

| Item | Reason deferred | Next step |
|---|---|---|
| Protect or retire the legacy `app.engines.review` flag/get routes | `DISTINCT_MODEL` — outside the "same-record bypass only" boundary this mission set | Future slice; note it has **live frontend callers** (tenant-portal, super-admin) |
| Customer flagging of other people's reviews | Would be invented policy | Product decision — `product-decisions-required.md` #2 |
| `staff` persona for review reply/flag | Would require a new permission | Product decision #1 |
| Flag deduplication per (review, actor) | Moderation-queue design | Product decision #3 |
| Final-state flag policy | No established policy to enforce | Product decision #4 |
| Provider reply editing / multi-reply | Explicitly prohibited from invention | Product decision #5 |
| Backfill `ReviewFlag.tenant_id` nulls + NOT NULL constraint | Requires a migration | Migration-enabled slice |
| `edit_review` validate-before-mutate ordering | Out of scope; no proven bypass | Small cleanup |
| Deep verification of `submit_review` tenant handling | Different capability | Slice covering customer review creation |
| Read-only UI gating audit | Frontend work prohibited | Frontend slice |
| Live E2E authorization tests | No DB/server in this environment | Run where a live stack exists |
| Slice-2D canaries | Explicitly prohibited | Requires `tenant-readonly-decision.md` conclusion |

## Remaining authorization queue
**7 modules / 17 routes** remain unprotected — see
`remaining-module-queue-update.csv`. No module was selected or begun; that is
the next discovery slice's job.
