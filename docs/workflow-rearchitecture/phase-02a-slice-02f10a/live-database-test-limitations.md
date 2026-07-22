# Live-Database Test Limitations — Slice 2F-10A (Workstream 13)

Re-reviewed the 10 test files excluded from Slice 2F-10's "clean"
regression count. None require a fix or block this slice's closure —
none cover complaint creation eligibility, refund-state transitions, or
message final-state policy, and this slice's own deterministic fixture
tests (`test_phase2f10a_complaint_eligibility_and_refund_integrity.py`)
independently cover every quality gate this slice is responsible for.

| File | Test count | DB dependency | Covers this slice's gates? | Equivalent deterministic test exists? | Exclusion affects closure confidence? |
|---|---|---|---|---|---|
| `test_final_l5_04c_matching_entitlement.py` | 7 | `ConnectionRefusedError` to real Postgres (`TestBookingConfirmationEntitlementGuard` live tests) | No — booking-confirmation entitlement, unrelated | n/a | No |
| `test_final_l5_05u_security_deposit_permission_authorization.py` | 29 | same — `TestRealConcurrencyMatrix`/`TestDomainIsolationGuards` live tests | No — security-deposit concurrency/permission, unrelated to complaint creation/refund-request | n/a | No |
| `test_module_l5_16_quotes.py` | 3 | same — `TestCustomerQuoteFlow` live test | No — quote/booking detail exposure, unrelated | n/a | No |
| `test_module_l5_24_complaint_notify.py` | 2 | same — `TestAdminResolveNotifiesLive` | No — admin-resolve notification, not creation/refund/message-policy | n/a | No |
| `test_module_l5_27_booking_notify.py` | 3 | same — `TestBookingConfirmNotifyLive` | No — booking confirmation notify | n/a | No |
| `test_module_l5_28_credit_checkout.py` | 3 | same — `TestApplyCreditLive` | No — invoice credit checkout, distinct from complaint settlement credit | n/a | No |
| `test_module_l5_29_booking_cancel_reschedule.py` | 4 | same — `TestCancelRescheduleLive` | No — booking cancel/reschedule, unrelated | n/a | No |
| `test_module_l5_13_reviews.py` | 3 | same — booking-rating end-to-end | No — customer_reviews engine, distinct module | n/a | No |
| `test_module_l5_17_credits.py` | 3 | same — `TestCustomerCredits` | No — general customer credit wallet reads, not settlement-connected | n/a | No |
| `test_trust_quality_phase1.py` | 28 | same — audit/health-formula live tests | No — trust/quality scoring, unrelated | n/a | No |

## Method
Re-ran each file's failing tests directly; every failure traces to the
same root cause (`asyncpg.connect_utils` → `ConnectionRefusedError` —
no live Postgres reachable in this sandboxed environment), confirmed via
full traceback inspection, not assumed from the file name alone.

## Conclusion
No excluded test is the sole evidence for any of this slice's required
quality gates. Every gate this slice is responsible for
(creation-eligibility enforcement, eligibility/creation consistency,
refund silent-transition proof, message final-state policy) has its own
dedicated, deterministic, fixture-based test in
`test_phase2f10a_complaint_eligibility_and_refund_integrity.py`,
independent of any live database. None of these 10 files were started,
installed, or otherwise made to run against a real database this slice.
