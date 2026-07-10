# FINAL-L5-01 — Remaining Blockers / Review Items

None of these block the core reset/seed/integrity/repeatability certification this sprint achieved, but all are real, honestly-documented gaps against the mission's full literal scope.

## Blockers to a full READY (require follow-up before broader Level-5 sign-off)
1. **Real browser smoke was not performed.** No Playwright/Chrome session verified any frontend page. See `FINAL_L5_01_CANONICAL_DATA_BROWSER_SMOKE_REPORT.md`.
2. **Frontend page-by-page data readiness was not exhaustively verified.** Only ~7 of ~40 mission-listed pages/areas were checked, and only at the API-response layer, not the rendered-UI layer. See `FINAL_L5_01_FRONTEND_DATA_READINESS_REPORT.md`.
3. **Configuration/rule data (Part 18) was not seeded at all** — health rules, badge rules, reward rules, standalone deduction-rule config, credit threshold rules, matching rules, notification policy. See `FINAL_L5_01_CONFIGURATION_RULE_DATA_REPORT.md`.
4. **Audit event seeding (Part 7's audit section) was not implemented** — no rows in `tenant_audit_logs`/`platform_audit_logs` etc.

## Real findings surfaced during this sprint (not fixed, since out of scope for a data-seeding sprint)
5. **RBAC gap**: `customer`-role user received `200 OK` (not `403`) from `GET /v1/admin/tenants`. Genuine backend authorization bug.
6. **Mission's assumed canonical route is wrong**: `/admin/home-services/service-jobs` returns 404; actual routes are `/v1/admin/service-job-assignments*`.
7. **~190 tenant-scoped tables lack FK constraints to `tenants(id)`** — referential integrity enforced entirely at the application layer for the majority of tables. This is why the first reset attempt silently left stale data behind. A real schema-hardening backlog item.
8. **Empty-database migration replay is blocked** by a `CREATE EXTENSION vector` superuser-privilege requirement. Environment-provisioning gap, not a migration-chain defect.
9. **Provider-level price range is single per-offering, not per-service-type** — `provider_enabled_offerings` cannot express distinct Split-AC vs Window-AC provider bounds; the admin `service_pricing_rules` remain the authoritative per-type source. Worth a schema review if per-type provider overrides are a real product requirement.
10. **Multiple notification-template-shaped tables exist** (`notification_templates`, `notif_event_templates`, `notification_template_versions`) without clear consolidation — carried from FINAL-L5-00's duplicate-code findings, re-confirmed this sprint.

## Process items
11. **This sprint's canonical seed initially caused a real test regression** (9 pytest errors) by reusing `admin@serviceos.local` with a different password than a pre-existing hardcoded test fixture expected. Caught and fixed within this sprint (password preserved as `Password123!` for that one account) — documented as a lesson, not hidden.
12. **Old/narrower seed scripts (`seed_phase0_baseline.py`, `serviceos_reset_dev_data.py`) were not archived** despite being functionally superseded for Level-5 purposes — kept per the "don't delete unproven-safe files" rule. See `FINAL_L5_01_OLD_SEED_FIXTURE_CLEANUP_REPORT.md`.
13. **No standalone integrity-check script was built** — checks were run ad hoc via inline Python this sprint. Recommend promoting to `scripts/verify_final_l5_01_integrity.py`.
14. **`data-integrity-results.json`/`api-smoke-results.json` cover a representative subset**, not the mission's full enumerated checklist (14 FK/orphan checks, ~20 uniqueness checks, 24 API smoke areas) — real numbers for what was actually checked, not padded to match the mission's full list.

## Not blockers — explicitly resolved this sprint
- Environment safety, backup, reset repeatability, seed idempotency, exactly-once deduction, ledger arithmetic, tenant isolation, orphan/duplicate checks (for the tables this sprint actually touched) — all proven with real evidence, not assumed.
