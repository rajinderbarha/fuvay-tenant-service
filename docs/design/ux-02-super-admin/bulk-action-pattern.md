# Bulk Action Pattern

Implemented inside `EnterpriseListPage` via the `bulkActions: {key,label}[]` prop (e.g. Tenant
List's "Suspend selected" / "Export selected").

## Flow
1. Row selection via checkboxes (DataTable's own selection support).
2. Choosing a bulk action shows an impact-preview step: how many rows selected, action name.
3. Confirmation step (explicit second click) before anything "happens".
4. Result step: a partial-success/failure detail list is the intended shape for a real
   implementation (e.g. "8 succeeded, 2 failed — reasons below"); in this MOCK_DESIGN_ONLY phase
   the result is always a simulated all-succeed message, clearly labeled design-only, since there
   is no backend mutation wired.

## Readiness
Always `MOCK_DESIGN_ONLY` regardless of the hosting list page's own readiness (e.g. Tenant List is
`READ_ONLY_READY` for its data, but its bulk actions remain mock).
