# Known Limitations — Slice 2F-10

1. **`add_customer_message` still allows messaging after
   `resolved`/`settled`** (only blocked on base `FINAL_STATUSES`) —
   symmetric with the provider-side open question from Slice 2F-9A, not
   decided here either.
2. **[RESOLVED IN SLICE 2F-10A]** Was: "`check_eligible`'s full policy
   (status window, complaint window, duplicate-open rejection) is not
   enforced at creation time, only ownership." Slice 2F-10A classified
   `check_eligible` as CANONICAL_CREATION_POLICY (not advisory) and wired
   it into `create_complaint` as the single authoritative gate — see
   `phase-02a-slice-02f10a/complaint-eligibility-contract.md`.
3. **No customer-facing evidence/media upload or read route exists** —
   reported as absent, not built (out of scope: "do not build a new
   dispute workspace").
4. **No customer-facing rework status read or independent rework
   decision route exists** — rework is reachable only as a side effect of
   accepting a rework-type resolution.
5. **[ADJUDICATED IN SLICE 2F-10A]** Was: "`create_refund_request_from_complaint`'s
   silent no-op on illegal transition (logs but doesn't raise) is
   pre-existing, unchanged." Slice 2F-10A investigated this directly and
   found it is deliberate, tested, load-bearing behavior shared by the
   whole refund lifecycle, not a defect — see
   `phase-02a-slice-02f10a/refund-silent-transition-review.md`. No code
   change was needed.
6. **Frontend `customer-app` component-level rendering was not
   exhaustively line-reviewed** — the backend is authoritative and
   already rejects illegal/repeated decisions cleanly; only the caller
   inventory and route-level exposure were audited (see
   `frontend-customer-exposure-audit.md`).
7. **`complaints.admin_router` was re-confirmed but not independently
   re-audited end-to-end** this slice (out of scope, per instruction).
8. **Global tenant-mutation remaining-module-count was not recomputed**
   this slice — would require a platform-wide re-audit beyond this
   router's scope.
