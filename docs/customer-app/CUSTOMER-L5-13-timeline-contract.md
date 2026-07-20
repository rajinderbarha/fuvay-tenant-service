# CUSTOMER-L5-13 — Timeline Contract (Execution Events)

## Endpoint

`GET /v1/customer/service-jobs/{jobId}/tracking` — real, returns
`{job, notes, media, timeline}`. This sprint parses only `job.status` and
`timeline[].{event_type, created_at}` — see contract-matrix.md for the
full field-exclusion rationale (the `notes` field, both top-level and
per-event, is not filtered by any `is_customer_visible` flag server-side,
unlike `ServiceJobExecutionNote`/`ServiceJobMediaUpload` — a real,
disclosed backend gap this client mitigates by never parsing it at all).

## Event-by-Event Contract

| Real `event_type` | Customer-safe label (client-authored, since this endpoint has no server-side label mapping unlike CUSTOMER-L5-12's assignment-engine timeline) | Rendered? |
|---|---|---|
| `job_accepted` | "Technician accepted the job" | Yes |
| `job_rejected` | "Provider is finding another technician" | Yes |
| `job_scheduled` | "Visit scheduled" | Yes |
| `technician_on_the_way` | "Technician is on the way" | Yes |
| `technician_reached_site` | "Technician has arrived" | Yes |
| `inspection_started` | "Inspection started" | Yes |
| `inspection_completed` | "Inspection completed" | Yes |
| `service_started` | "Service in progress" | Yes |
| `work_done` | "Work completed" | Yes |
| `customer_not_available` | "Technician couldn't reach you at the scheduled time" | Yes |
| `job_cancelled` | "Booking cancelled" | Yes |
| `job_failed` | "Booking couldn't be completed" | Yes |
| `quote_required`/`parts_required` | "Provider needs your approval to continue" | Yes (parts-approval execution itself remains out of scope) |
| `diagnosis_added`/`before_photo_uploaded`/`after_photo_uploaded`/`work_note_added` | *(unmapped)* | **No** — real events, but execution detail (notes/media), not status milestones; this sprint's scope is the milestone timeline only |

## Fail-Safe Handling

Unlike CUSTOMER-L5-12's assignment-engine timeline (where the *backend*
itself drops unrecognized event types before they ever reach the client),
this endpoint returns **every** real event type, including the
notes/media ones this sprint deliberately doesn't map. This client's own
`resolveExecutionEventLabelKey` therefore performs the filtering
client-side — an unmapped event type returns `null` and is filtered out of
the rendered array (never shown as a raw internal string), with a safe
`execution_event_unmapped` warning logged for observability. Verified by
a dedicated test (`execution-event-labels.test.ts`'s "fails safe on an
unmapped-but-real event type" case).

## Ordering

Backend-guaranteed (`get_job_timeline`'s own `ORDER BY created_at ASC`,
`execution/home_service_service.py`) — this client renders the array
exactly as received, no client-side re-sort.

## Accessibility and Localization

Same treatment as CUSTOMER-L5-12's timeline: plain text rows (label +
optional timestamp), a purely decorative checkmark icon, fully
understandable without color or icons. Unlike L5-12's assignment-engine
labels (real, backend-authored, but English-only), this sprint's own
client-authored labels are properly localized into English/Hindi/Punjabi
from the start, since this client owns the label text.

## Test Coverage

`execution-timeline-schema.test.ts` (5 tests) and
`execution-event-labels.test.ts` (3 tests) cover the real parsing,
internal-field stripping, empty-timeline, per-item resilience, and
event-label fail-safe behavior.
