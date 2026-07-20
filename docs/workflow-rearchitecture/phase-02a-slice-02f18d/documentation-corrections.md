# Documentation Corrections

## Corrections to Slice 2F-18C's documentation
Per this slice's mission, the following 2F-18C claims are
corrected/qualified (files remain, annotated with a pointer to this slice
— not deleted or rewritten):

- **`SECURITY_DOMAIN_INTEGRITY_AND_PRIVACY_CLOSED_PRODUCT_POLICY_BLOCKED`**
  (2F-18C's final status): 2F-18C's `SECURITY_CLOSED` claim rested on the
  thread-claim lock alone, without restricting WHO could perform the
  first claim, and without atomic claim creation. This slice's mission
  explicitly says not to claim security closure while "an arbitrary
  authorized viewer may make the first claim into an unrelated
  conversation" and not to claim domain-integrity closure while
  "two concurrent requests can claim one asset for different threads."
  2F-18C's status is preserved as an honest record of what was true then;
  this slice closes both gaps.
- **2F-18C's `view-versus-share-authority.md`** treated
  `MediaAccessService.assert_can_view` plus the thread-claim lock as
  sufficient evidence for a first-use claim — CORRECTED: an ADDITIONAL
  first-use destination-authority check (technician uploader-match) is
  now required, since view authority alone does not prove the CALLER
  chose the right destination.
- **2F-18C's `known-limitations.md` item 1** ("Unclaimed `chat_attachment`
  assets remain tenant-wide viewable") — CORRECTED for technician: no
  longer tenant-wide; requires uploader match. Office remains tenant-wide
  (documented as an intentional, unchanged design choice, not an
  oversight).
- **2F-18C's implicit treatment of claim creation as atomic** — CORRECTED:
  2F-18C's `db.get()`-based lookup had NO row lock; this slice adds
  `SELECT ... FOR UPDATE`, making the claim-application pass genuinely
  race-safe.
- **2F-18C's claim-writer audit** was never performed at all (no
  dedicated document existed) — this slice performs it for the first time
  (`claim-writer-audit.csv`) and discovers/fixes the `replace_asset` gap
  (a same-tenant "replace"-authorized user could swap a claimed asset's
  content without thread authority).

## No prior slice's coverage arithmetic was found incorrect
200/226 (2F-18 through 2F-18C's figure) is CONFIRMED, not corrected, by
this slice's independent, route-by-route reconciliation
(`canonical-coverage-reconciliation.md`) — now with the cumulative
evidence of all five slices in this series.

## This slice's own approval-gate annotation convention
Per this initiative's established pattern, 2F-18C's `approval-gate.md` is
annotated below with a note pointing to this slice.
