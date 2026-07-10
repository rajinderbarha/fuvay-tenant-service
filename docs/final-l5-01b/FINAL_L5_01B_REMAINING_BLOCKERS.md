# FINAL-L5-01B — Remaining Blockers

## Blockers to unconditional READY

1. **Admin dashboard/tenants pages 404 in live browser session** (BUG-006) — not diagnosed. Highest-priority follow-up: re-run the browser smoke spec in a clean session without this sprint's server-restart churn, and if it persists, investigate frontend routing/build state directly.
2. **Only 1 of 6 required browser sessions attempted** — Tenant Owner, Tenant Read Only, Customer One, Customer Two, Technician One real-browser flows were not run this sprint.
3. **4 of 10 rule domains have no backing schema** (Reward Rules, Credit Threshold Rules, Provider Verification Rules, standalone Notification Policy) — requires a schema-design decision, not fixable by seeding alone.
4. **Empty-database replay incomplete** — bootstrap privilege issue fully solved, but a separate pre-existing migration bug (`service_setup_templates` duplicate, BUG-004) blocks reaching `head` from empty. Not patched this sprint per the "no rewriting applied migrations" rule.
5. **Customer-to-Customer and Technician-to-Technician isolation not specifically tested** this sprint (structurally supported by seed data, but no explicit negative-access automated test was written).
6. **13 of 17 fixed RBAC endpoints not individually parametrized** into the automated regression suite (same fix pattern, not each independently asserted).
7. **Frontend TypeScript/build not re-verified this sprint** (no frontend files changed, so FINAL-L5-00's last-known-good result stands but wasn't re-run).
8. **Live-server verification limitation**: this sprint's sandboxed tool environment could not reliably restart/control the shared dev server process (Bash and PowerShell tool invocations run in separate process namespaces). All backend fixes are verified via in-process automated tests (authoritative) but live curl/browser re-verification against a freshly-restarted shared server (outside this session) is recommended.
9. **Customer-facing Low/Mid/High price-option formula** not independently re-derived from the live pricing-resolution service (carried from FINAL-L5-01).
10. **~190-table missing-FK gap** formally tracked (this sprint's register) but not remediated — by design, per the mission's own instruction not to add FKs blindly.
11. **Legacy `jobs`/`field_ops` routes not deprecated** — real endpoints for the canonical `service_jobs` system exist and cover every role, but the legacy parallel system remains live and undeprecated (consumer audit needed first).
12. **3 browser console errors captured but not individually classified** during the one browser smoke run performed.

## Not blockers — explicitly resolved this sprint
- Customer-to-Admin RBAC vulnerability: fixed, 21/21 automated regression tests passing.
- Migration bootstrap privilege gap: fixed and verified via real reproduction.
- Canonical rule seed (6 of 10 domains): seeded, idempotent, proven via 2 consecutive runs.
- Canonical jobs source-of-truth: documented, real endpoints confirmed for all 4 roles, no code gap found.
- Reset/seed/rule-seed repeatability: proven across 3 consecutive full cycles.
- Ledger arithmetic and exactly-once deduction: unchanged and re-confirmed.
- Tenant isolation (tenant-to-tenant): unchanged and structurally intact.
