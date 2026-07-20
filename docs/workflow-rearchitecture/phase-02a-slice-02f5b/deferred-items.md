# Deferred Items — Slice 2F-5B

Explicitly deferred to a future slice/phase, per the user's out-of-scope
list — none of these were investigated, designed, or acted on:

1. `package_commerce.admin_router` verification (its own future slice).
2. Granting `FINANCE_PAYOUTS_*` or `FINANCE_CLAIMS_*` to `admin_finance`
   (a product-policy decision, see `product-decisions-required.md`).
3. Any new finance permission or new tenant finance role (`tenant_finance`).
4. Remediation of `readonly@demo-ac-services.local`.
5. Migration 144.
6. Finance UI visual redesign.
7. Maker-checker / dual-control workflow design.
8. Payout/payment-gateway behavior changes or new payout mechanisms.
9. Monetization-model changes.
10. Ledger-history rewrites or merging finance models.
11. Booking/job pipeline changes.
12. Admin or Tenant "My Work" features.
13. Beginning any new router module beyond `finance_hub.admin_router`.
14. Deep internal audit of `platform_commerce.CommerceService`'s
    `approve_claim`/`reject_claim`/`admin_adjust_deposit` amount/state
    logic (delegated-into, not owned by finance_hub).
15. `approve_payout`'s unbounded `approved_amount` follow-up (flagged,
    not fixed — see `known-limitations.md` item 4).
