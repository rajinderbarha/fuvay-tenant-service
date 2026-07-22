# Canonical Coverage Reconciliation

- Denominator: 313 → **321** (honest, +8 evidence-backed additions this
  slice, all from `app/engines/auth/router.py`).
- Protected: 313 → **321** (all 8 additions use the same
  already-verified-safe guard pattern: `require_tenant_mutation_permission`
  / `require_permission` + explicit server-derived `tenant_id` check).
- Unprotected: **0** (unchanged — no gap found in any of the 8 additions).
- `verify_2f37.py`'s own hardcoded 313/313 assertions (R13/R19/R20) were
  **not updated** this slice — that script belongs to Slice 2F-37's frozen
  verifier scope, and this slice's mission explicitly scopes route-census
  verifier work to a *new* `verifier-spec.md`/`verifier-report.md` rather
  than editing 2F-37's. This means `verify_2f37.py` will now report
  "313/313" against a codebase that actually has 321 confirmed canonical
  mutations — a stale-but-not-wrong statement (313 is still fully a
  subset of 321; nothing regressed), recorded honestly here rather than
  silently left inconsistent. See `known-limitations.md`.
