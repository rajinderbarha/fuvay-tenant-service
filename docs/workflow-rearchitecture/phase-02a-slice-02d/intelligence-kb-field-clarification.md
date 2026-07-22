# Intelligence KB Field Clarification — Slice 2D

## Chosen action: code documentation + regression test (safest compatible option)

Per Workstream 11's own preference ordering ("choose the safest compatible action") and explicit prohibition on renaming the DB field without fully understanding compatibility impact (not assessed this slice — `allowed_roles_json` is read/written by `kb_service.py` and serialized via `to_dict()`; a rename would need every caller and any external consumer of the KB admin API updated in lockstep, not attempted here):

1. **Added an in-code docstring/comment directly on the model column** (`app/engines/analytics/intelligence_models.py`) stating unambiguously: "DISPLAY_ONLY... NOTHING... reads it back to gate retrieval, visibility, or authorization... must never be treated as an access control... If real enforcement is ever built, it must go through app.core.permissions." This is the comment a future developer will see the moment they open the model file — the highest-visibility, lowest-risk clarification available.
2. **Added a regression test** (`tests/test_phase2d_tenant_access_model.py::TestIntelligenceKBFieldNotAuthoritative`) statically asserting `kb_service.py`'s source never contains an authorization-shaped comparison against this field (`allowed_roles_json ==`, `in kb.allowed_roles_json`). If a future change adds such a comparison, this test fails, forcing a deliberate decision rather than an accidental slide into "it's secretly enforced now."

## Not done this slice
- **Response alias**: no additional API response key was added (e.g. `allowed_roles_json_display_only`) — the existing `to_dict()` output was left unchanged to avoid any API-contract change without assessing every consumer.
- **Deprecation migration**: no schema change was made — renaming or dropping the column is explicitly out of scope until compatibility impact is understood.
- **User-facing label rename**: the admin UI's "Allowed Roles" multi-select label (`frontend/super-admin/app/admin/intelligence/page.tsx`) was not touched this slice — this is a legitimate, low-risk follow-up (e.g. relabeling to "Content Targeting Roles (display only)") but was left for a dedicated frontend-facing slice rather than folded into a backend-focused access-model closure slice, to keep this slice's diff auditable and scoped.

## Verification
`tests/test_phase2d_tenant_access_model.py::TestIntelligenceKBFieldNotAuthoritative::test_kb_service_never_checks_allowed_roles_json_for_authorization` — passing.
