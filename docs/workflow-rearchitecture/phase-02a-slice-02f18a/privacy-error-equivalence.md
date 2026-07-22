# Privacy-Error Equivalence

## Fixed this slice
`ChatThreadService.validate_thread_access`'s every denial branch (customer,
technician, provider/staff, generic participant fallback) now raises
`ERR_CHAT_THREAD_NOT_FOUND` instead of `ERR_CHAT_THREAD_ACCESS_DENIED`.
Combined with `get_thread`'s own pre-existing "genuinely missing" check
(which already raised `ERR_CHAT_THREAD_NOT_FOUND`), EVERY thread-access
failure path — missing, foreign-tenant, same-tenant non-participant,
unassigned technician, removed participant — now produces the exact same
`error_code` and, via `app/exceptions.py`'s generic domain-code-to-status
mapping (`_domain_code_status`: any code containing `NOT_FOUND` → 404), the
exact same HTTP status (404).

Verified directly:
- `test_foreign_tenant_and_missing_thread_share_error_code` — both a
  literally nonexistent thread ID and a real-but-foreign-tenant thread ID
  raise `ValueError(ERR_CHAT_THREAD_NOT_FOUND)`.
- `test_thread_not_found_maps_to_404_not_403` — proves the actual HTTP
  status mapping, not just the raised Python exception.

## Public HTTP behavior (traced, not just service-layer)
| Scenario | error_code | HTTP status | Content disclosed |
|---|---|---|---|
| Missing thread | `CHAT_THREAD_NOT_FOUND` | 404 | none |
| Foreign-tenant thread | `CHAT_THREAD_NOT_FOUND` | 404 | none |
| Same-tenant non-participant thread (technician) | `CHAT_THREAD_NOT_FOUND` | 404 | none |
| Unassigned technician on a real job thread | `CHAT_THREAD_NOT_FOUND` | 404 | none |
| Removed participant | `CHAT_THREAD_NOT_FOUND` | 404 | none |
| Missing message | `CHAT_MESSAGE_NOT_FOUND` | 404 | n/a — no route accepts a bare message ID as a target, this code is only reachable internally via `moderate_message` (admin-only, not reachable from this router) |
| Missing notification | `IN_APP_NOTIFICATION_NOT_FOUND` | 404 | none — already unified pre-2F-18 (only ONE error code exists for both "missing" and "not yours", `mark_notification_read`'s WHERE clause makes them indistinguishable by construction) |
| Missing attachment | `CHAT_ATTACHMENT_NOT_FOUND` | 404 | none |
| Foreign-tenant attachment | `CHAT_ATTACHMENT_NOT_FOUND` (same code, this slice) | 404 | none |

## What is intentionally NOT unified
Notification preference validation errors
(`NOTIFICATION_PREFERENCE_INVALID`, 2F-18) and visibility validation errors
(`CHAT_MESSAGE_INVALID_VISIBILITY`, 2F-18) are input-validation errors, not
existence/ownership errors — no privacy concern applies to them (they don't
reveal whether any particular record exists), so they were left as
distinct, descriptive codes (422, per `_domain_code_status`'s default
branch).
