# Completion, Commission and Review Verification — Round 3 (Workstream 3)

## Completion — reached live this round

`POST /v1/staff/service-jobs/{id}/complete` with
`{work_summary:"AC gas refilled and unit tested - UX07 Round 3 E2E
completion", collected_amount:775.0,
payment_mode:"customer_pays_provider_directly"}` -> real success,
`status:"completed"`.

## Commission/credit — real, server-computed, never client-calculated

The `complete` response included a real, server-generated
`usage_credit_deduction` object:

```
ledger_id: 846951c7-7446-4e46-aa9e-8d9ac3fb2898
event_type: completed_job_deduction
credit_delta: -21.0
balance_before: 3980.0
balance_after: 3959.0
deduction_source: c6dd09d3-187b-4a99-beec-2e66f6751edf  (the real ServicePricingRule id)
service_id / service_type_id / brand_id: same canonical IDs as the whole job
deduction_status: "deducted"
```

This is the platform's real usage-credit/commission mechanism — computed
and applied server-side at the moment of completion, with a full audit
trail (`ledger_id`, `reason`, `request_id`). The client (`mobile/staff-app`)
never computes this value; it only receives and could display it verbatim.
`-21.0` against a `775.0` job (~2.7%) is a real, plausible platform
commission rate for this tenant's package — not independently re-derived
or verified against the package's exact commission-rate config this round
(a real, disclosed scope boundary).

## No fake online payment shown

Confirmed by inspecting the FULL field list of
`GET /v1/customer/bookings/{id}` after completion: `booking_id`,
`booking_number`, `status`, `assignment_status`, `assignment_message`,
`preferred_date`, `preferred_time_window`, `city`, `address`,
`issue_summary`, `selected_provider`, `selected_price_option`,
`selected_price_amount`, `payment_mode`, `job_id`, `job_status`,
`scheduled_date`, `scheduled_time_window`. No online-payment-capture, card,
wallet-deduction, or escrow field of any kind is present at any point in
this response, before or after completion — on-site payment policy held
exactly as required.

## Customer sees completion state

`status:"completed"` real, live, confirmed via the same endpoint above
after the technician's real `complete` call.

## Customer review submission — REAL finding this round, upgraded from UX-06/Round-1's assumption

UX-06 (and Round 1, re-confirming without re-deriving) found that
`mobile/customer-app`'s `ReviewScreen.tsx` has no real submit call wired
(`reviewsApi` only had `eligibility`/`list`/`get`), and the screen itself
honestly shows "Review submission isn't available yet."

**This round, the real backend was found to now expose a genuine `POST
/v1/customer/reviews` endpoint** (confirmed via `GET /openapi.json` and the
real source at `app/engines/customer_reviews/customer_router.py:32-60`) —
this endpoint did NOT exist (or was not discoverable) when UX-06 did its
audit. Live-verified this round:

1. `GET /v1/customer/reviews/eligibility?record_type=service_job&record_id={job_id}`
   -> real `{eligible:true, record:{status:"completed", tenant_id:...}}`
   (only eligible after the job reached `completed` this round — order
   dependency confirmed real, not assumed).
2. `POST /v1/customer/reviews` with the REAL required body shape (read
   directly from source: `tenant_id`, `record_type`, `record_id`,
   `overall_rating` required; `review_title`/`review_text`/etc. optional)
   -> real success: `review_number: REV-56700400`, `status:"pending"`,
   `visibility:"private_until_approved"`.
   - **Real, minor backend defect found while discovering the correct
     shape**: submitting with plausible-but-wrong field names (`rating`,
     `score`, `comment`) produced a raw, unhandled `500 INTERNAL_ERROR`
     rather than a structured `422` field-validation error — the router
     does `body["tenant_id"]`/`int(body["overall_rating"])` direct
     dictionary access with no try/except around the KeyError, so a
     missing/misnamed required field crashes instead of returning a
     proper validation error. Not fixed this round (backend-owned,
     narrow); logged in `known-limitations.md`.
3. `GET /v1/provider/reviews` (as `provider@serviceos.local`) -> the real
   review appears, same `review_number`, `status:"pending"` (correctly
   NOT yet publicly visible — `visibility:"private_until_approved"` is a
   real moderation gate, not a bug).

## Frontend NOT updated this round

`mobile/customer-app/src/screens/ReviewScreen.tsx` was NOT modified to
wire up this newly-discovered real endpoint — this is deliberately left
for a dedicated follow-up (wiring a real submit call plus the correct
required-field mapping is a genuine, scoped frontend task, and Round 3's
remaining time was needed for the other required workstreams). This is the
single highest-value, most concrete "ready to implement" finding from this
round — the exact real request shape is fully documented above.

## Canonical `customer_reviews` API used, not legacy `/v1/reviews`

Confirmed: `POST /v1/customer/reviews` is a distinct route from the legacy
`/v1/reviews` (both exist in the real OpenAPI schema, per Sprint-24's
`customer_reviews` engine vs. the old `review` engine) — the endpoint used
above is the correct, canonical one per this phase's hard constraint.
