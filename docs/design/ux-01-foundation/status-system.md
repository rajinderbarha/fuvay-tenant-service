# Status System

Single source of truth: `statusRegistry` in `frontend/packages/
design-system/src/tokens/motion.ts`.

| Status | Tone |
|---|---|
| active, approved, completed | success |
| pending, in_review | warning |
| scheduled, in_progress | info |
| rejected, cancelled, failed, suspended | danger |
| draft, archived, expired | neutral |

## Component: `StatusBadge`
`<StatusBadge status="..." variant="badge" \| "dot" \| "tone-text" />`.
Looks up the status (case/space/hyphen-insensitive) in the registry; if the
value is **not** registered it does not throw or render blank — it falls
back to a `neutral` tone and a humanized version of the raw string (e.g.
`"some_new_status"` → `"Some New Status"`). This was chosen deliberately so
a backend introducing a new status value never breaks the UI; it just looks
neutral until someone adds it to the registry.

## Governance
New statuses must be added to `statusRegistry`, not hardcoded per-page — see
`design-governance-rules.md`.
