# offering_type_id Required-Field Contract Defect — Root Cause (Workstream 11)

## Root cause, precisely identified this round

`app/engines/home_service_booking/service.py::_get_required_field_list`
(line 1274) and its sibling `_compute_missing_fields` (line 1285) both
gate whether `offering_type_id` is required on a single per-offering
database flag: `offering.is_type_required` (a boolean column on the
`master_services` table).

Direct query against the real dev database confirms, for `ac_repair`
(`master_service_id a96e625a-60e1-46c0-bde4-ccbb88da50a2`):

```
slug: ac_repair
is_brand_required: True
is_type_required: False   <-- the actual root cause
requires_issue_type: True
```

`is_type_required` is `False` for this offering — so the draft's
`required_fields` response correctly (per its own contract) omits
`offering_type_id`. BUT the real, live `ServicePricingRule` rows for this
exact `master_service_id` are BOTH scoped to a specific `service_type_id`
("Split AC" / "Window AC", per Round 1's finding), with no unscoped
fallback row. `match-and-price`'s pricing-rule resolution
(`_spr_specificity`, lines ~679-714) discards any `ServicePricingRule` whose
`service_type_id` is set but doesn't match the draft's `offering_type_id` —
and since a null `offering_type_id` can never match a non-null
`service_type_id`, NO rule is ever eligible when `offering_type_id` is
omitted, producing the real `422 PRICE_OPTIONS_UNAVAILABLE` Round 1 hit.

## Answering the brief's specific investigation questions

1. **Where does `offering_type_id` become required?** Not in the draft's
   declared contract at all (`is_type_required:False`) — it becomes
   FUNCTIONALLY required only later, inside `match-and-price`'s pricing-rule
   lookup, because of how the real `service_pricing_rules` data for this
   offering happens to be scoped.
2. **Why does the required-fields contract omit it?** Because
   `is_type_required` is a data flag on `master_services`, set (at some
   catalog-configuration time) to `False` for `ac_repair` — apparently
   without anyone cross-checking it against how `ac_repair`'s actual
   `ServicePricingRule` rows would later be scoped. This looks like a
   catalog-data-entry inconsistency, not a code logic bug: the CODE
   correctly derives `required_fields` from `is_type_required`; the DATA
   value of `is_type_required` for this specific offering doesn't match
   the DATA reality of its own pricing rules.
3. **Was another canonical field intended?** No — `offering_type_id` is
   the correct, existing, canonical field; there is no evidence a
   different field was meant to carry this information.
4. **Which backend module owns the defect?** `app/engines/home_service_booking`
   (the required-fields/missing-fields logic) for the code path, and
   whichever catalog-configuration surface sets `is_type_required`
   per-offering (likely `app/engines/admin_catalog` or a super-admin
   service-setup screen) for the underlying DATA inconsistency.
5. **Do ALL services require it, or only selected offerings?** Only
   selected offerings — `is_type_required` is a per-`master_service` flag,
   not global. `ac_repair` has it `False` (inconsistent with its own
   pricing-rule scoping); other offerings may have it `True` and be
   perfectly consistent (not individually re-checked this round for every
   offering — a real, disclosed scope boundary).
6. **User-visible failure behavior:** a real, generic `422
   PRICE_OPTIONS_UNAVAILABLE: "This service does not have pricing
   configured yet."` — which is misleading: pricing DOES exist, it's just
   unreachable without a field the API itself said wasn't required. A real
   customer using the real SmartBot/booking flow for `ac_repair` without
   ever being asked for an AC type would hit this exact wall.
7. **Security/pricing impact:** none directly (no way to manipulate price
   via this gap — it's a hard failure, not a bypass), but it is a genuine
   BLOCKING functional defect for any real customer trying to book
   `ac_repair` through a client that trusts the declared `required_fields`
   contract (which is the correct, intended client behavior).
8. **Minimal safe backend remediation options** (NOT implemented this
   round, per the brief's explicit instruction):
   - Option A (data fix): set `is_type_required = True` for `ac_repair` (and
     audit all other offerings whose real `ServicePricingRule` rows are
     type-scoped with no unscoped fallback, to catch the same class of bug
     elsewhere) — smallest, most targeted fix, a pure data correction.
   - Option B (code fix): make `_get_required_field_list` also require
     `offering_type_id` whenever ANY eligible `ServicePricingRule` for the
     offering is type-scoped (a live catalog check rather than a static
     flag) — more robust against future catalog-config drift, but a real
     code change with wider blast radius.
   - Option C (fallback pricing): add an unscoped (`service_type_id IS
     NULL`) fallback `ServicePricingRule` for `ac_repair` so
     `offering_type_id` becomes genuinely optional again, matching what
     `is_type_required:False` currently promises — valid if the product
     intent is that AC type should be optional for repair (plausible: a
     repair call might not need to know AC type upfront, unlike an
     installation).
   - Recommend Option A as the minimal, safe, immediate fix, with Option C
     as the better long-term product answer if "AC type genuinely optional
     for repair" is the intended behavior.
9. **Required tests for a backend slice**: (a) a test asserting
   `required_fields` and `match-and-price`'s actual field dependency stay in
   sync for every real offering (a contract-consistency test, not just a
   single-offering regression test); (b) a specific regression test for
   `ac_repair` covering exactly this scenario; (c) a test that any
   catalog-config change to `is_type_required` is validated against the
   offering's real `ServicePricingRule` scoping at write time (preventing
   this class of drift going forward).

## Frontend behavior this round (fail-safe, no invented data)

`mobile/customer-app`'s real flow was NOT modified to invent, guess, or
silently default `offering_type_id` — Round 1's workaround (explicitly
supplying the real "Split AC" `offering_type_id` after diagnosing the gap)
was a MANUAL curl step for diagnosis purposes only, not a frontend code
change. The actual `DeepSeekChatScreen.tsx` production code path was not
altered to auto-select an offering type; it still relies on the real
`required_fields` contract and SmartBot's own tool-orchestrated flow to ask
the customer for whichever fields the backend declares. This means: a real
customer booking `ac_repair` through the actual app today will hit the same
real `422` this round diagnosed, unless/until the backend-owned fix above
is applied. This is the correct, safe, "fail loudly and honestly rather
than fabricate" behavior — not fixed on the frontend because there is no
frontend-owned fix available (the frontend cannot know to ask for a field
the backend's own contract says isn't required).
