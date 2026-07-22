# Notification/Thread Read Privacy (updated from 2F-18)

## What changed
2F-18's `notification-read-privacy.md` flagged one gap: `GET
.../chat/threads/{id}` distinguished missing vs. foreign-tenant threads by
error code/status. **Fixed this slice** — both now return
`CHAT_THREAD_NOT_FOUND` / 404 (see `privacy-error-equivalence.md`).

## Updated table
| Read | Tenant/recipient isolation | Assignment (technician) | Foreign/missing privacy-equivalent |
|---|---|---|---|
| `GET /v1/provider\|staff/notifications` | `user_id == caller` | n/a (self-scoped) | n/a (list) |
| `GET .../unread-count` | as above | n/a | n/a |
| `GET .../preferences` | as above | n/a | n/a |
| `GET .../chat/threads` (provider/staff) | `tenant_id == caller` (office persona, tenant-wide by ratified policy) | n/a | n/a (list) |
| `GET .../chat/threads` (technician) | **participant-scoped, NOT tenant-wide (fixed this slice)** | list reflects existing participant rows only (see `known-limitations.md` for the reassignment-timing caveat) | n/a (list) |
| `GET .../chat/threads/{id}` | tenant match (office) / live assignment or active participant (technician, fixed this slice) / `customer_id` match (customer) | enforced (technician) | **YES — fixed this slice** |
| `GET .../chat/threads/{id}/messages` | as above (via thread) | as above | **YES — fixed this slice**, plus per-message visibility filtering now correctly technician-aware (`content-visibility-policy.md`) |
| `GET .../audit-logs` | `tenant_id == caller` | n/a (technician cannot reach — provider-only route) | n/a (list) |
| `GET .../audit-logs/record-timeline` | as above | n/a | n/a |

## GET routes produce no mutation
Re-confirmed unchanged — no GET handler in any of the 3 routers calls
`db.add`/`db.commit`/any write-returning service method (same conclusion as
2F-18, re-verified against the modified `chat_service.py`).
