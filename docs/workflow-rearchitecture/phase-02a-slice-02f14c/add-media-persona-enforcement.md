# add_media Persona Policy

## Supported personas

Identical structure to `add_note`: `tenant_owner` (tenant-wide, own tenant), `staff`/
`technician` (assigned-Job only), `super_admin` (platform-wide). `customer` is explicitly
denied (`MEDIA_ACCESS_DENIED`, 403, Slice 2F-14A).

## Fixed this slice

Same router-level gap and same fix as `add_note`: `require_staff_or_above_mutation` added.

## Verified

- Tenant-wide vs. assigned-Job authority: same as `add_note`.
- Assignment enforcement: `_assert_can_access_job`'s `_assert_assigned` branch, unmodified.
- Job ownership: same mechanism as `add_note`.
- Media/reference ownership: `add_media`'s `media_id` parameter is an optional, opaque,
  unvalidated UUID reference with **no FK constraint and no lookup against any other table**
  anywhere in this codebase (re-confirmed this slice, unchanged from Slice 2F-14A's
  `evidence-media-boundary.md`/`jobmedia-access-control.md` findings). There is nothing to
  "substitute" — the field is stored as-is and never dereferenced to fetch or serve real content.
  This is disclosed, not silently assumed safe (see known-limitations.md).
- Tenant ownership of the media/reference: `JobMedia.tenant_id` is always derived from
  `job.tenant_id` (Slice 2F-14A fix, unmodified) — never client-supplied.
- Final-Job behavior: no state guard on media attachment, same reasoning as notes (an audit
  trail, not a lifecycle-gated action).
- Customer visibility: `JobMedia` has no `is_internal`-equivalent column (unchanged limitation,
  carried from Slice 2F-14A/14B) — any actor who can access the Job at all sees all its media.
  Documented as a product decision, not fixed (no new column/migration built, per this slice's
  explicit "do not add a JobMedia visibility column" instruction).
- Denied calls create no `JobMedia`: verified via `test_no_mutation_on_denied_add_media` (Slice
  2F-14A, re-verified) and this slice's `test_customer_still_denied_add_media`.
- Unknown roles/scopes fail closed: `require_staff_or_above_mutation` denies any role not in
  its admitted set (mirrors `require_staff_or_above`'s existing fail-closed behavior).

## Final classification

**FULLY_PROTECTED_ROUTER_AND_SERVICE** for ownership/persona/scope. The customer-visibility
column gap remains an explicitly disclosed product limitation, not a security defect (job-level
tenant/assignment/customer-exclusion ownership IS enforced — only a finer-grained
internal-vs-customer split within an already-authorized viewer is absent).
