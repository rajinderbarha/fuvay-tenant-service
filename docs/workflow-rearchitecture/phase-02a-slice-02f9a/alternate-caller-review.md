# Alternate Caller Review — Slice 2F-9A

## Search performed
`grep -rn "provider_add_response|provider_offer_resolution" --include="*.py"`
across the full repository.

## Result
Both service methods have exactly one production caller each:
- `provider_add_response` ← `provider_router.py`'s `respond_to_complaint`
  only.
- `provider_offer_resolution` ← `provider_router.py`'s `offer_resolution`
  only.

No other router, background job, scheduler, admin tool, or script calls
either method. No weaker or alternate caller exists that could bypass the
guards fixed/verified in this slice.

## `complaints.customer_router` reference point (not audited, not modified)
`customer_router`'s equivalent capability
(`add_customer_message`/`get_customer_complaint`) already contains the
identical `FINAL_STATUSES` guard this slice added to
`provider_add_response` — confirmed by direct source read (the guard was,
in fact, the pattern this slice's fix was mirrored from). This is
recorded as a reference point only, per the mission's explicit
instruction not to begin a broad audit of `complaints.customer_router` in
this slice. It is not classified as "weaker" — it is the same or stronger
than what this slice enforces for the provider side.

## Not investigated (explicitly out of scope)
`complaints.admin_router`'s own message/resolution equivalents (if any)
were not searched, per the "do not modify complaints.admin_router"
constraint — Slice 2F-9 already confirmed this router is
`require_super_admin`-gated throughout, a stronger boundary, and it was
not touched this slice either.
