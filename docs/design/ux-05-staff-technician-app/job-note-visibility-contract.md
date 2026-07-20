# Job Note Visibility Contract

`JobNoteComposer` (new this session) enforces the internal / technician / customer_visible distinction from both
directions:
- **Composition**: a visibility picker defaults to `"technician"` (the least customer-exposed non-internal
  option) -- a note is never silently posted as customer-visible by omission.
- **Display**: every rendered note carries an explicit uppercase visibility tag (`INTERNAL`, `TECHNICIAN`,
  `CUSTOMER_VISIBLE`) directly above its text -- no note can render ambiguously.

No cross-tenant note leakage is possible in this design (all fixture data is scoped to a single job/tenant;
no note-fetch-by-tenant-wildcard code path exists).

**Gap**: no live job-notes endpoint exists (`API_CONTRACT_REQUIRED`). `JobNotesMediaShowcaseScreen` composes to
local state only and is dev-only, not linked from production nav.
