# Behavioral Invariant Report

- **Admitted-role sets unchanged on every guard swap.**
  `require_tenant_mutation_permission` reuses each route's exact
  pre-existing permission (`TENANT_UPDATE`, `TENANT_BILLING_READ`,
  `TENANT_BILLING_MANAGE`); `require_mutation_access_scope` adds no role
  restriction — used only where none existed before.
- **`StaffPermission` explicit-deny semantics untouched** — no change to
  `permission_checker` or `app/core/permissions.py`'s `has()` logic; no
  new permission or guard function was added this slice.
- **M01/N01/geo/2F-35/2F-36 closures untouched** — no file under
  `app/engines/auth/`, `app/engines/media/`, `app/engines/geo/`,
  `app/engines/webhook/`, `app/engines/rag/`, `app/engines/security/`,
  `app/engines/document/`, `app/engines/enterprise_grid/`,
  `app/engines/admin_catalog/`, `app/engines/profile/`,
  `app/engines/marketing_automation/`, `app/engines/analytics/`,
  `app/engines/chat/`, `app/engines/inventory/`,
  `app/engines/appointment/`, `app/engines/service_catalog/`,
  `app/engines/dispatch/`, `app/engines/data_science/`,
  `app/engines/settings_engine/`, or `app/engines/notification/` was
  modified this slice.
- **N01 domain-integrity backlog intentionally frozen, not remediated**
  — per the frozen 2F-34 contract; see `n01-final-status.md` for the full
  reasoning on the conflict between this run's verbose mission prompt and
  the actual frozen ground truth.
- **Set C routes (20, mostly already closed by prior slices) byte-
  identical** — confirmed by verifier condition R16.
- **`compliance` deletion/portability workflows: existing product policy
  reused, not invented** — the DPDP right-to-erasure/portability
  implementation already existed; this slice only closed a missing
  self-only ownership check, adding no new retention/deletion policy.
- **9 application files touched**: `app/engines/platform_commerce/
  {router,service}.py`, `app/engines/pricing/{router,service}.py`,
  `app/engines/payment/{router,service}.py`,
  `app/engines/subscription/{router,service}.py`,
  `app/engines/compliance/router.py`.
