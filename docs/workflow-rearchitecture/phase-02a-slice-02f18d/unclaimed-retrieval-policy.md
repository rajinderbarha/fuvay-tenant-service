# Unclaimed Retrieval Policy

## Composed policy for `chat_attachment` assets with no claim (implemented in `MediaAssetService._assert_chat_thread_authority`)

```
if actor.role == "super_admin": allow
meta = asset.metadata_json (fail closed if not a dict)
thread_id = meta.get("chat_thread_id")
if thread_id is falsy:                      # UNCLAIMED
    if actor.role == "technician":
        require asset.uploaded_by_user_id == actor.user_id, else deny
    # all other roles: MediaAccessService.assert_can_view's result
    # (already computed before this method runs) stands unmodified
    return
# ... claimed-asset path unchanged from 2F-18C ...
```

## Requirements checklist
- Uploader/owner access is explicit — `assert_can_view`'s uploader
  fallback branch (existing, unmodified) plus this slice's technician
  uploader-match requirement makes it EXPLICIT rather than incidental for
  technicians specifically.
- Customer-owner access is explicit — `assert_can_view`'s customer-context
  branch (existing, unmodified): exact `customer_id` match required.
- Tenant owner/staff access is explicit and least-privilege — "least
  privilege" here means the EXISTING tenant+customer-context match (not
  arbitrary cross-tenant access); this slice did not further restrict
  office access, consistent with the ratified, unmodified office policy
  established since 2F-18B.
- Assigned technician behavior is explicit — **THIS SLICE**: assignment
  to the Job is NOT sufficient for unclaimed-asset access; uploader
  identity is required.
- Unassigned technician is denied — true both before AND after this slice
  (fails `assert_can_view`'s tenant-context check only if not the
  uploader either way; in practice an unassigned technician typically
  also fails `validate_thread_access` before this question is even
  reached for the ATTACH path, though the RETRIEVAL path can be reached
  independently via a known `media_id` if the asset is UNCLAIMED — this
  is exactly why this slice's fix matters for retrieval specifically, not
  just attach).
- Tenant membership alone is denied (for technician) — **THIS SLICE**,
  the core fix.
- Foreign customer and foreign tenant are denied — `assert_can_view`
  (existing, unmodified).
- Missing and denied remain privacy equivalent — unchanged from 2F-18C;
  this slice's new technician-denial path flows through the SAME
  `except ServiceOSException` → `NotFoundException` unification for
  `chat_attachment` context.

## No thread authority applied when no thread exists
Confirmed: the unclaimed branch returns (or denies, for technician)
WITHOUT ever attempting to resolve or query a `ChatThread` — there is no
thread to check authority against, and the code does not attempt to
fabricate one. `db.get.assert_not_called()` proves this directly for the
office-persona unclaimed case
(`test_unclaimed_asset_skips_thread_check_for_office_persona`, 2F-18C
file, re-passing this slice).
