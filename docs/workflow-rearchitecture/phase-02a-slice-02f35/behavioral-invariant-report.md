# Behavioral Invariant Report

- **Admitted-role sets unchanged on all 10 `require_permission`→`require_
  tenant_mutation_permission` swaps.** Same underlying `permission_
  checker.has()` call; only the access-scope layer is new.
- **Admitted-role set unchanged on `rag_query`.** `require_mutation_
  access_scope` wraps the same `get_current_user` dependency; only the
  access-scope layer is new.
- **`StaffPermission` explicit-deny semantics untouched** — no change to
  `permission_checker` or `app/core/permissions.py`'s `has()` logic.
- **`MediaAccessService`/`MediaService`/N01, `GeoService`/geo closures
  untouched** — no media or geo file was modified this slice.
- **`WebhookEndpoint`/`APIKey`/`Document`/`KnowledgeBase`/`KBDocument`
  field allow-lists unchanged** — only WHERE-clause predicates and
  constructor context changed; no new column, no schema change, no
  migration.
- **Set C routes (21) byte-identical** — confirmed by verifier condition
  R03 (no Set C route was newly protected).
- **Only 8 application files touched**: `app/engines/webhook/{router,
  service}.py`, `app/engines/rag/{router,service}.py`,
  `app/engines/security/{router,service}.py`,
  `app/engines/document/{router,service}.py`, plus one internal-caller
  fix in `app/engines/field_ops/service.py`, plus the canonical/matrix
  CSV tracking artifacts (not application code).
