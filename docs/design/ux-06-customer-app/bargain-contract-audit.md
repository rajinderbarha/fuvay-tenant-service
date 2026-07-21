# Bargain Contract Audit — UX-06 Round 5 (Workstream 1)

Read directly (not inferred from UI): `app/engines/home_service_booking/service.py`
(`mark_ready_for_confirmation`, `match_provider_and_price`, `confirm_price_choice`,
`resolve_price_estimate`), `app/engines/home_service_booking/customer_router.py`
(`/{draft_id}/confirm`), `app/engines/final_records/creation_service.py::finalize`,
`app/engines/admin_catalog/models.py::BargainRule`,
`app/engines/admin_catalog/auto_price_options_router.py`.

## Key correction to Round 3/4's understanding

There are **two different confirm endpoints**:
- `POST /v1/customer/home-services/booking-drafts/{draft_id}/confirm` (real,
  in `home_service_booking/customer_router.py`) — the correct one. It calls
  `mark_ready_for_confirmation()` THEN `finalize()` in one request.
- `POST /v1/customer/confirm/home-service-booking/{draft_id}` (in
  `final_records/confirm_router.py`) — what Rounds 3/4 used. This ONLY calls
  `finalize()`, which requires `draft.status == "ready_for_confirmation"`
  already — a precondition that can only be reached via the FIRST endpoint's
  `mark_ready_for_confirmation()` call. Calling the second endpoint directly,
  as prior rounds did, was always going to fail with `FINAL_DRAFT_NOT_READY`
  regardless of pricing config. **This was a real client-side routing mistake
  in addition to the missing BargainRule**, both real findings, both now
  documented and corrected in this round.

## Is bargain optional?

**No — not for the `home_service_booking` (ServiceBooking/ServiceJob) pipeline.**
`mark_ready_for_confirmation()` (`service.py:822-892`) hard-requires:
```python
if not draft.selected_tenant_id or not draft.price_snapshot or "price_options" not in draft.price_snapshot:
    raise ServiceOSException(ERR_NO_PROVIDER_AVAILABLE, "No matched provider/price options found ...")
selected_tier = (draft.booking_summary or {}).get("selected_price_tier")
if selected_tier not in ("low", "mid", "high"):
    raise ServiceOSException("INVALID_SELECTED_PRICE_OPTION", ...)
```
There is no code path that allows `finalize()` to succeed from the plain
`resolve_price_estimate()` catalog-default price alone — `match_provider_and_price()`
(which produces `price_options`) and `confirm_price_choice()` (which sets
`selected_price_tier`) are both mandatory steps in this real pipeline, not
optional haggling. **What IS optional** is genuine customer-initiated
negotiation/counter-offering — nothing in `confirm_price_choice` accepts a
customer-supplied amount; the customer only picks one of the server-computed
`low`/`mid`/`high` tiers. So: "haggling" is optional (there is no
counter-offer UI required), but "select one of the 3 backend-computed price
tiers via match-and-price" is a mandatory infrastructure step, and it
hard-depends on `match_provider_and_price()` finding a `BargainRule` with
`customer_min_price`/`customer_max_price` set for the `master_service_id`.

## Is the frontend incorrectly forcing bargain?

No — `DeepSeekChatScreen.tsx`'s Round 3/4 flow never called `match-and-price`/
`confirm-price-choice` at all (it went straight from `price-estimate` to
`confirm`), which is why the wrong endpoint's rejection looked like a bargain
problem. The frontend was not over-forcing bargain; it was under-calling the
mandatory provider-matching step and calling the wrong confirm route.

## BargainRule scope (critical for Workstream 3)

`app/engines/admin_catalog/models.py:645` — `BargainRule` has **no `tenant_id`
column at all**. It is keyed by `category_id`/`master_service_id`/
`pricing_rule_id` only — a platform-wide policy per service, not a
per-tenant one. Any `BargainRule` created for `ac_repair` would apply to
**every tenant** offering `ac_repair`, not just the isolated DEMO tenant.

## Who may create one / is there a safe endpoint?

`auto_price_options_router.py` only exposes READ/preview endpoints
(`PRICING_BARGAIN_EVALUATE_PREVIEW` permission) — **no create/write endpoint
for `BargainRule` exists anywhere in the mounted routes** (grepped the whole
`app/` tree). Creating one would require either a migration-adjacent admin
tool not present in this codebase, or a direct DB insert into a genuinely
shared, platform-wide canonical table.

## Conclusion (feeds bargain-optionality-decision.md)

Workstream 3's conditions ("rule can be scoped to the isolated demo tenant")
**cannot be satisfied** — the model has no tenant scoping at all, and no safe
API exists to create one. Per the spec's own instruction ("When ANY condition
cannot be proven, do NOT create the rule"), no `BargainRule` was created this
round.
