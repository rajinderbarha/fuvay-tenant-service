# BookingStatusHistory Schema

## Model
`app/engines/booking/models.py::BookingStatusHistory`, table `booking_status_history`, `ServiceOSBase` (provides `id` UUID primary key and `created_at`/`updated_at` timestamps — confirmed base class, not redefined per-model).

```python
class BookingStatusHistory(ServiceOSBase):
    """APPEND-ONLY. Every booking state transition. Full lifecycle queryable."""
    __tablename__ = "booking_status_history"
    __table_args__ = (Index("ix_bsh_booking_id", "booking_id"),)

    booking_id:      Mapped[uuid.UUID]      = mapped_column(UUID(as_uuid=True), nullable=False)
    tenant_id:       Mapped[uuid.UUID]      = mapped_column(UUID(as_uuid=True), nullable=False)
    from_status:     Mapped[str | None]     = mapped_column(String(30), nullable=True)
    to_status:       Mapped[str]            = mapped_column(String(30), nullable=False)
    changed_by:      Mapped[uuid.UUID|None] = mapped_column(UUID(as_uuid=True), nullable=True)
    changed_by_role: Mapped[str | None]     = mapped_column(String(30), nullable=True)
    reason:          Mapped[str | None]     = mapped_column(String(500), nullable=True)
    meta:            Mapped[dict]           = mapped_column(JSONB, default=dict, nullable=False)
```

| Field | Nullable | Notes |
|---|---|---|
| `id` (from `ServiceOSBase`) | No | Primary key |
| `booking_id` | No | FK by convention (not a declared `ForeignKey`, matches the codebase's general style of UUID references without DB-level FK constraints) |
| `tenant_id` | No | Denormalized from the Booking for query efficiency |
| `from_status` | **Yes** | `NULL` exactly once per Booking — at creation. Every other write passes the Booking's real current status. |
| `to_status` | No | The new status this row records |
| `changed_by` | Yes | The acting user's ID (`self.actor_id`) — nullable because some system-triggered transitions may run with no authenticated actor (not observed in the current codebase, but the column allows it) |
| `changed_by_role` | Yes | The acting user's role (`self.actor_role`) at the time of the write — **this is the field this slice's provenance checks depend on** |
| `reason` | Yes | Free-text, human-readable |
| `meta` | No (defaults `{}`) | JSONB, transition-specific extra data (e.g. `preflight_passed`, `reschedule_count`) |

There is **no dedicated event/action enum field** distinct from the `(from_status, to_status)` pair — the "event type" is inferred structurally, not stored as a label. This is why `from_status IS NULL` (not any enum value) is the mechanism used to identify the creation event specifically.

## Event representations
| Event | `from_status` | `to_status` | Write site |
|---|---|---|---|
| Creation | `NULL` | `booking.status` (initial, e.g. `PENDING_CONFIRMATION`) | `create_booking`, line ~624 |
| Confirmation | real prior status | `BS.CONFIRMED` | `confirm_booking`, line ~769 |
| Rejection | real prior status | `BS.REJECTED` | `reject_booking`, line ~810 |
| Cancellation | real prior status | `BS.CANCELLED` | `cancel_booking`, line ~865 |
| Reschedule (accepted) | `b.status` (current, unchanged) | `b.status` (same value — status doesn't change on reschedule, only slot/date) | `accept_reschedule`'s underlying logic, line ~1122 |
| Conversion to Job | `BS.CONFIRMED` | `BS.CONVERTED_TO_JOB` | `convert_to_job`, line ~1052 |
| Void | real prior status | `BS.VOIDED` | `void_booking`, line ~1213 |

There is no separate write for "customer note" or "reschedule REQUEST" (as opposed to accept) — `add_note` writes to the distinct `BookingNote` table, not `BookingStatusHistory`; `request_reschedule` creates a `BookingRescheduleRequest` row but does **not** call `_write_history` at all (confirmed by grep — no `_write_history` call inside `request_reschedule`). This means a reschedule *request* by a customer never touches `BookingStatusHistory` and cannot possibly be mistaken for a creation event.

## All writers
Exactly one write site: `BookingService._write_history` (line 90-97), called from 6 call sites within `app/engines/booking/service.py`: `create_booking` (from_s=None), `confirm_booking`, `reject_booking`, `cancel_booking`, the reschedule-accept status-refresh path, `void_booking`. No other module writes to this table (confirmed via repo-wide search for `BookingStatusHistory(`).

## All readers
- `BookingService.get_timeline` (line ~1146) — full ordered history for display, `ORDER BY created_at`.
- `BookingService.convert_to_job`'s creator-role check (line ~922-926).
- `BookingService.create_booking`'s relationship-requirement check (line ~500-511).
- `FieldOpsService._assert_tenant_customer_relationship` (line ~152-160).
- `FieldOpsService.create_job`'s direct `booking_id` provenance check (line ~448-465).

## Can the model distinguish the 7 listed event types?
**Yes**, structurally, via `(from_status, to_status)`: creation is the unique `from_status IS NULL` row; confirmation/rejection/cancellation/void are each a unique `to_status` value; reschedule-accept is the only case where `from_status == to_status` (a same-value transition, distinguishable from creation because `from_status` is populated, not NULL). Customer *notes* and reschedule *requests* (as opposed to accept/reject) are not represented in this table at all — they live in `BookingNote`/`BookingRescheduleRequest` respectively, so they cannot appear in a `BookingStatusHistory` query and cannot be confused with any of the above.
