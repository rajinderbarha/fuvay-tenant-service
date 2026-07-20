# Known Limitations - Slice 2F-31

1. **N01 is not fully closed.** 2 of 9 Set A routes remain open
   (permission-file dependency); all 3 Set B routes remain unprotected
   (router/service outside the allow-list). Status is
   `SECURITY_CLOSED_DOMAIN_INTEGRITY_BLOCKED`, not the fully-closed status.
2. **Database/storage atomicity is not proven**, and this slice does not
   attempt to prove or fix it - stated explicitly rather than assumed.
3. **No live object-storage evidence.** Guard-level proofs are live; deep
   two-tenant DB/storage scenarios for Set B were not executed.
4. **The storage-key tenant prefix is client-influenced** on
   `initiate_upload` (documented in storage-authority-audit.csv), not fixed.
5. Set B `confirm_upload` accepts no actor/tenant parameter at all - a
   structural gap in the service method's own signature, not just its guard.
6. This slice selects no next module and does not extend the allow-list.
