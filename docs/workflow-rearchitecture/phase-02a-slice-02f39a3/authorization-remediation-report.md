# Authorization Remediation Report — Slice 2F-39A3

## Fixed this slice (2 real defects, confirmed and closed)

### 1. `ChatService.delete_message` — missing sender-ownership check

Its sibling `edit_message`, in the same file, already correctly checks
`msg.sender_id != self.actor_id` before allowing an edit. `delete_message`
had no equivalent check — any authenticated user (in the message's tenant,
per the `tenant_id` filter) could soft-delete any other user's message.
Fixed to match `edit_message`'s existing pattern exactly. 2 new tests.

### 2. `compliance.router::record_consent` / `withdraw_consent` — missing self-service check

Slice 2F-37 already fixed this exact class of gap for `request_deletion`/
`request_export` in the same file (`compliance.router`) — client-supplied
`user_id` with zero comparison to the caller's own identity. `record_consent`
and `withdraw_consent` were apparently missed at the time. Independently,
this exact gap was documented as unremediated since Slice 2F-26D/F/G/H's
`security-observations-not-remediated.md` ("withdraw another user's
consent; mirrors the `POST /v1/compliance/consent` observation").
Fixed with the identical established pattern (self-service only, super_admin
exempt). 4 new tests.

## Flagged, NOT fixed this slice (21 routes, `PRODUCT_DECISION_REQUIRED`)

See `known-limitations.md` for the full list and reasoning. In summary:
~8 routes use a bare `require_permission(...)` where sibling routes in
the same file correctly use `require_tenant_mutation_permission(...)` —
the exact same class of defect confirmed twice already this program
(`security.router::create_api_key`, `pricing.router::activate_rule`/
`deactivate_rule`). These were **not** blindly fixed this slice: each
requires the same rigor applied to the confirmed defects (tracing the
service layer to confirm there is no other compensating check, as was
done for `security.router`'s `rotate_api_key`/`revoke_api_key`, which
turned out to already be safe via `_require_trusted_tenant` despite an
identical-looking router signature). Given time constraints, this
tranche prioritized breadth of classification over exhaustive
verification of every guard-mismatch candidate.

The remaining ~13 flagged routes are bare-`get_current_user` mutations
not individually traced to a service-layer ownership check this slice
(distinct from the ones that *were* traced and confirmed safe, e.g.
`chat.router::mark_read`/`set_typing`, `enterprise_grid.router::cancel_export`/
`retry_export`).

## Not re-litigated (explicitly out of scope, unchanged)

`media.router::initiate_upload`/`confirm_upload`, `media.new_router::delete_media`
— N01 domain-integrity backlog territory. Remains
`SECURITY_CLOSED_DOMAIN_INTEGRITY_BLOCKED` per the standing N01 status,
not reopened by this slice.
