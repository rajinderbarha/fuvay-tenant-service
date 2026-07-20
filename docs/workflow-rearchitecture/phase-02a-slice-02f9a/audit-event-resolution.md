# Audit Event Resolution — Slice 2F-9A

## Finding
Slice 2F-9's `known-limitations.md` and `deferred-items.md` claimed
`provider_add_response` "does not log an event," unlike the other 8
mutation paths in `complaints.provider_router`. Direct re-reading of
`complaint_service.py` in this slice disproved that claim.

## Disposition: EXISTING_AUDIT_EVENT_CONFIRMED
`provider_add_response` (line ~338) calls:
```python
await self._log_event(db, complaint_id, tenant_id, ACTOR_PROVIDER, actor_user_id,
                      EVT_PROVIDER_RESPONDED, None, None, None, None, request_id=request_id)
```
This writes a `ComplaintEvent` row identically to every other mutation
path in this service. Proven directly (not asserted) in
`test_audit_event_logged_on_success`, which spies on `svc._log_event` and
confirms exactly one call with `event_type == "provider_responded"`.

## `provider_offer_resolution`'s audit event
Also confirmed correct and pre-existing:
```python
await self._log_event(db, complaint_id, tenant_id, ACTOR_PROVIDER, actor_user_id,
                      EVT_RESOLUTION_PROPOSED, None, None, None, {"type": resolution_type},
                      request_id=request_id)
```
Fires only after `self._transition(...)` succeeds — so no audit event is
ever written for a rejected (illegal-state) resolution offer, which is
correct (an audit event implying a completed mutation must not be
written when no mutation occurred).

## Action taken
No new audit event was added — none was missing. Slice 2F-9's
documentation was corrected in place (see
`phase-02a-slice-02f9/known-limitations.md` item 4 and
`phase-02a-slice-02f9/deferred-items.md` item 12).
