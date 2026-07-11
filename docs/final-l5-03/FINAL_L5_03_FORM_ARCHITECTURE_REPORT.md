# FINAL-L5-03 — Shared Form Architecture Report

## Current state (audited, not restructured this sprint)
No schema-validation library (react-hook-form, zod, yup) exists in any of the 3 apps — forms use plain controlled `<input>`/`<Select>` components with `useState`, inline required-field checks (`if (!email || !password) { setError(...); return; }` — confirmed this exact pattern in every login page touched this sprint), and backend-authoritative validation for everything business-relevant (price min≤max, date ordering, etc. — confirmed not duplicated in frontend, see Business Rule Duplication Report).

## Mapped against the mission's required capabilities
| Capability | Status |
|---|---|
| Schema validation | Not implemented (no library) — inline required-checks only |
| Server field-error mapping | Ad-hoc per form (reads `err.context` where the backend provides field-level detail) |
| Dirty-state tracking | Not implemented as a formal concept; some forms compare current vs. loaded values inline |
| Save/discard behavior | Present per-form (e.g. `SetupWizardDrawer`'s edit flows), not via a shared hook |
| Read-only mode | Implemented via `isTenantReadOnly()` disabling submit buttons, not a form-level "readOnly" prop system |
| Autosave for future wizards | Not implemented — explicitly future work per the mission's own framing ("Autosave support for future wizards") |
| Accessible labels | `<label>` elements present on every form field checked this sprint |
| Required indicators | `required` HTML attribute used (native browser validation as first line, backend as authority) |
| Help text | Present ad-hoc, not a shared "help text" slot convention |
| Loading state | `loading` boolean + disabled submit button, consistent pattern across every login/mutation form touched this sprint |
| Success feedback | Toast/inline confirmation per-page |

## Frontend early-guidance validations confirmed backend-authoritative (not duplicated)
Required values, date/time ordering, price min≤max — all confirmed backend-validated in the Business Rule Duplication scan; no frontend form in this sprint's scope independently recalculates or enforces these as authoritative.

## Result
Forms are consistent in *pattern* (native controlled inputs + inline validation + backend authority) across all 3 apps, but not built on a shared abstraction. This is documented as the current standard; introducing a form library is real future work (would touch every form in 3 apps), not a cleanup fix — flagged in the Deprecation/Developer Guide as a recommendation, not attempted here.
