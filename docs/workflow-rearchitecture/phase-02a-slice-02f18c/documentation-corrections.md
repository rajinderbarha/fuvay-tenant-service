# Documentation Corrections

## Corrections to Slice 2F-18B's documentation
Per this slice's mission, the following 2F-18B claims are
corrected/qualified (files remain, annotated with a pointer to this slice
— not deleted or rewritten):

- **`SECURITY_DOMAIN_INTEGRITY_AND_PRIVACY_CLOSED_PRODUCT_POLICY_BLOCKED`**
  (2F-18B's final status): 2F-18B's `SECURITY_CLOSED` claim rested on
  `assert_can_view` being treated as sufficient for attachment use — this
  slice's mission explicitly says redistribution authority is a DISTINCT
  question `assert_can_view` doesn't answer. 2F-18B's status is preserved
  as an honest record of what was true then; this slice strengthens the
  underlying evidence (view-vs-share distinction, thread-claim lineage,
  retrieval-time equivalence) rather than retroactively invalidating it.
- **2F-18B's `known-limitations.md` item 2** ("Technician tenant-wide
  media view... classified as pure product policy, not narrowed") —
  CORRECTED for the retrieval path: technician access to CLAIMED
  `chat_attachment` assets is now assignment/participant-scoped, not
  tenant-wide. The classification is downgraded from "pure product
  policy" to "security fix, with a narrower residual product-policy
  window" (unclaimed assets only).
- **2F-18B's `known-limitations.md` item 4** ("Removed chat participants
  may retain generic media view authority... classified as product-only")
  — CORRECTED: now enforced for claimed `chat_attachment` assets (see
  `participant-removal-revocation.md`).
- **2F-18B's `attachment-download-read-authority.md`** claimed the media
  engine's retrieval-path privacy gap was "unrelated to chat privacy" and
  out of scope — CORRECTED: this slice's mission explicitly identifies it
  as directly blocking `platform_notifications` privacy closure, and it
  has been fixed (scoped to `chat_attachment` context).
- **2F-18B's `product-decisions-required.md` item 5** (`staff_send_message`
  dropped `media_ids`) — RESOLVED this slice (SAFE_SUPPORT).

## No prior slice's coverage arithmetic was found incorrect
200/226 (2F-18/2F-18A/2F-18B's figure) is CONFIRMED, not corrected, by
this slice's independent, route-by-route reconciliation
(`canonical-coverage-reconciliation.md`) — now with the strongest evidence
yet (sharing, recipient, retrieval, and revocation dimensions all closed
or narrowly, honestly disclosed).

## This slice's own approval-gate annotation convention
Per this initiative's established pattern, 2F-18B's `approval-gate.md` is
annotated below with a note pointing to this slice.
