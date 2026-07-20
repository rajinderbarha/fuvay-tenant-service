# Provider-Assisted Provenance Regression

Preserved rule (unchanged from 2F-15A/B, re-verified this slice with the actor-bound predicate):

- Creation event remains provider-authored — `changed_by_role == "tenant_owner"` (or whichever non-customer role performed the creation), never rewritten.
- The Booking is never reclassified as customer-created — the creation-history row is append-only and the actor-binding filter (`changed_by == Booking.customer_id`) only makes the check STRICTER, never allows a provider-created Booking to newly qualify.
- Independent prior relationship evidence excludes the current Booking (`Booking.id != b.id` / `_Booking.id != booking.id`, unchanged).
- Later customer actions do not change origin (unaffected by this slice — see 2F-15B's `later-customer-activity-test-matrix.csv`, still valid).
- Conversion and field_ops relationship use recheck independent evidence at each authority-dependent action (unchanged design).

## Direct tests (this slice)
| Case | Test | Result |
|---|---|---|
| Provider-assisted Booking, valid independent evidence | `test_provider_created_booking_with_independent_evidence_passes_gate` (2F-15A, re-verified with updated mock shape) | Gate passes, conversion proceeds |
| Provider-assisted Booking, no independent evidence | `test_convert_to_job_creator_check_uses_bound_query_not_role_alone` (new) / `test_provider_created_booking_without_independent_evidence_rejected` (2F-15A, updated mock) | `CUSTOMER_TENANT_RELATIONSHIP_REQUIRED`, zero persistence |
| Evidence supplied only by the current Booking | Structurally impossible — the independent-evidence query explicitly excludes `Booking.id != b.id` / `_Booking.id != booking.id`; the current Booking can never satisfy its own evidence requirement (proven at every prior slice gate since 2F-15A, unchanged this slice) | Excluded by query construction |
| Evidence belonging to another tenant | The independent-evidence query filters `Booking.tenant_id == b.tenant_id` — a Booking from a different tenant can never match, regardless of customer_id | Excluded by query construction (unchanged, pre-existing tenant scoping) |
| Conflicting creation history | See `conflicting-creation-history-matrix.csv` | Fails closed in every category |
| Missing creation history | `test_convert_to_job_creator_check_uses_bound_query_not_role_alone` (mocked `None` result) | Falls through to independent-evidence check, fails closed if absent |

No regression: all pre-existing 2F-15A/2F-15B provider-assisted-provenance tests pass unchanged after the actor-binding fix (mock shape updated where the query's return semantics changed from "raw role string" to "match-or-None," but the tested BEHAVIOR — which scenarios pass/fail — is identical).
