# Job Pipeline Boundary — field_ops.Job vs ServiceJob/Booking/PartsRequest

## Finding

`field_ops.Job` (table `jobs`, `app/engines/field_ops/models.py`) is a distinct pipeline from
`ServiceJob`. Confirmed via direct model-import inspection of `FieldOpsService`:

```python
from app.engines.field_ops.models import Job, JobStatusHistory, JobNote, JobMedia, JobQuote, JobChecklistItem
```

No import of `ServiceJob`, `ServiceBooking`, or `Booking` appears in `field_ops/service.py`'s
job-mutation path. `PartsRequest` (from the ServiceJob pipeline, per Slice 2F-13 and earlier)
has no foreign key to `field_ops.Job` and is never referenced by `field_ops/service.py` or
`field_ops/staff_router.py`.

`Booking.convert_to_job()` (in `app/engines/booking/service.py`) is the one legitimate, existing
bridge: it copies `credit_applied`/`payable_amount` from `Booking` onto a newly-created
`field_ops.Job` row at creation time. This is a one-directional, one-time creation copy, not an
ongoing adapter, and it pre-dates this slice (documented in the P0 job-completion sprint). No
new bridge was created or needed this slice.

## Similarly-named but separate state machines

Both `field_ops.Job` and `ServiceJob`/`Booking` use words like "status", "checklist", and
"complete", but they are independent state machines with independent enum values, independent
tables, and independent completion gates. This slice did not merge them, did not translate Job
IDs to ServiceJob IDs, and did not build any cross-pipeline completion logic.

## Explicitly not touched this slice

- `PartsRequest` — remains ServiceJob-only.
- `quote_checklist` — untouched, distinct from `JobChecklistItem`.
- `Booking`/`ServiceBooking` lifecycle — untouched.
- `checklist_router` (ServiceChecklistTemplate/Item, Slice 2F-13) — untouched except for
  inspection to re-confirm the boundary; no shared bypass was found requiring a fix there.
