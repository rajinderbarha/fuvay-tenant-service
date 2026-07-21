# Deferred Items

- Classification of the remaining 229 routes across 32 modules — deferred
  to one or more future slices, prioritized roughly by UNVERIFIED count:
  `field_ops.router` (28), `platform_commerce.router` (23),
  `pricing.router` (17), `security.router` (12),
  `quote_checklist.provider_router` (11), `booking.router` (11), then the
  remaining smaller modules.
- Dedicated tests + service-layer-bypass review for the 5 auth.router
  additions that only have guard-pattern evidence
  (`invite_staff`/`update_permissions`/`deactivate_staff`/`resend_invite`/
  `update_staff_schedule`).
- Updating `verify_2f37.py`'s hardcoded 313/313 to 321/321 (requires
  deciding whether to edit the frozen 2F-37 verifier or build a
  successor).
- A dedicated `verify_2f39a.py`.
- A second full-backend-regression run.
- All items already deferred by Slice 2F-39 (13 domain failures, 2
  frontend version-pin items, 2 TS-compile items) remain deferred,
  unchanged.
