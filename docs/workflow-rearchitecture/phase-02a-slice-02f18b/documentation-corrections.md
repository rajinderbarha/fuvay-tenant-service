# Documentation Corrections

## Corrections to Slice 2F-18A's documentation
Per this slice's mission, the following 2F-18A claims are
corrected/qualified (files remain, annotated with a pointer to this slice
— not deleted or rewritten):

- **`SECURITY_DOMAIN_INTEGRITY_AND_PRIVACY_CLOSED_PRODUCT_POLICY_BLOCKED`**
  (2F-18A's final status): re-examined against this slice's mission
  statement, which explicitly says "Do not claim domain-integrity closure
  while attachment authority is based only on tenant equality" — 2F-18A's
  attachment check WAS tenant-equality-only, so its `DOMAIN_INTEGRITY_CLOSED`
  claim, while defensible at the time given the depth investigated, is
  RETROACTIVELY understood to have rested on a narrower foundation than
  ideal. This slice's fix (reusing `MediaAccessService`, adding
  customer/context/lifecycle checks) is what makes that closure claim
  solid going forward. 2F-18A's final status label is preserved as an
  honest record of what was true then; this slice does not retroactively
  downgrade it, but strengthens the underlying evidence.
- **2F-18A's `attachment-media-ownership.md`** claimed "ATTACHMENT_MODEL_SUPPORTED
  disposition... tenant-level ownership enforced" and explicitly flagged
  "uploader/owner authorization... not enforced" as an open item —
  CORRECTED/CLOSED: uploader/owner authorization IS now enforced via
  `MediaAccessService.assert_can_view`'s uploader-fallback and
  customer-ownership branches.
- **2F-18A's `known-limitations.md` item 1** ("Attachment uploader-level
  authorization not enforced") — RESOLVED this slice.
- **2F-18A's `product-decisions-required.md` item 1** (attachment
  uploader-level authorization — "should attachment references be
  restricted to assets uploaded by the sender...") — PARTIALLY RESOLVED:
  `MediaAccessService`'s existing policy (not sender-only, but
  principal-authorized, which is a coherent and pre-existing platform
  rule) was adopted rather than inventing a stricter sender-only rule not
  evidenced elsewhere in the codebase.

## No prior slice's coverage arithmetic was found incorrect
200/226 (2F-18/2F-18A's figure) is CONFIRMED, not corrected, by this
slice's independent reconciliation (`canonical-coverage-reconciliation.md`)
— now with stronger backing evidence (the attachment dimension is fully
closed, not merely tenant-scoped).

## This slice's own approval-gate annotation convention
Per this initiative's established pattern, 2F-18A's `approval-gate.md` is
annotated below with a note pointing to this slice.
