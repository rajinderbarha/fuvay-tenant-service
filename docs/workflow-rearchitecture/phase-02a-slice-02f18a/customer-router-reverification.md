# Customer Router Reverification

| Requirement | Status | Evidence |
|---|---|---|
| Canonical customer role | Enforced | `require_customer` (2F-18, unchanged) |
| Principal-derived customer identity | Enforced | `uuid.UUID(u.user_id)` passed as both `actor_user_id` and `customer_id` — never body-supplied |
| Thread/notification recipient ownership | Enforced | `mark_notification_read`'s `WHERE user_id=caller`; `validate_thread_access`'s `RECIP_CUSTOMER` branch (`thread.customer_id == actor_user_id`) |
| Conversation participant membership | Enforced (implicitly via `customer_id` match — customers are not participant-row-scoped like technicians, they're directly owner-scoped via `ChatThread.customer_id`) | unchanged from 2F-18 |
| Parent Booking/Job ownership | Enforced | `create_thread`'s 2F-18 record-ownership check (customer_id must match resolved record's customer_id) |
| Internal visibility filtering | Enforced | `is_visible_to("customer")` excludes `admin_only`/`provider_only` |
| Foreign record privacy | **Fixed this slice** | `validate_thread_access`'s `RECIP_CUSTOMER` branch now raises `ERR_CHAT_THREAD_NOT_FOUND` (was `ERR_CHAT_THREAD_ACCESS_DENIED`) |
| No tenant mutation-scope dependency | Confirmed | `TestCustomerRouterObjectOwnership::test_customer_router_does_not_import_tenant_mutation_dependency` — proves NO route in `customer_router.py` depends on `require_owner_or_office_staff_mutation` |
| No provider impersonation | Confirmed | `actor_type=RECIP_CUSTOMER` hardcoded server-side in `customer_router.py`, never client-supplied |
| No customer access to staff-internal records | Confirmed | `is_visible_to` excludes customer from `admin_only`/`provider_only`; `validate_thread_access`'s customer branch is `customer_id`-gated, cannot reach a thread it doesn't own regardless of visibility settings |

## Conclusion
"Applying `require_customer` alone is not sufficient without object
ownership" — this mission statement is satisfied: `require_customer`
(role gate) is layered under the SAME `customer_id`/`validate_thread_access`
object-ownership checks used everywhere else in this module, not a
standalone role check.
