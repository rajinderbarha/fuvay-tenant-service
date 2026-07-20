# N01 confirm_upload Storage-Existence — Status: NOT REMEDIATED (frozen)

Per `n01-final-status.md`, this item is frozen (re-confirmed still open)
this slice, not remediated, per the explicit "do not remediate" / "N01
media files explicitly OUT" instruction in the frozen Slice 2F-34
`slice-2f37-implementation-contract.md`.

## Known issue (unchanged from Slice 2F-31A/32/33/34)

`MediaService.confirm_upload` materializes a `MediaFile` DB row without
verifying the referenced storage object actually exists. A client can
call confirm_upload after only creating an upload session, without ever
uploading the file, and the system will record a `MediaFile` as if the
upload succeeded.

## What would be required to close this (for a future scoped slice)

- Verify the upload session belongs to the authoritative tenant/actor.
- Verify the session is not expired/already consumed.
- Derive the expected object key server-side.
- Call the storage adapter to confirm the object exists in the
  configured bucket/container.
- Validate size/content-type against the session where authoritative.
- Reject confirmation on a foreign tenant's object key.
- Ensure a missing object or storage error does not create a `MediaFile`
  row.
- Document the storage/DB non-atomicity honestly (two-phase, not a
  single transaction).

None of this was implemented this slice.
