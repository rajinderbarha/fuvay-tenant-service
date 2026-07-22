# Provider Reply Authority — Slice 2F-24

## The defect

`POST /v1/provider/reviews/{review_id}/reply` was guarded by bare
`get_current_user`. Any authenticated principal — including a **`customer`**
— could post the official provider reply to a review.

The impersonation was not merely cosmetic. `ReviewService.submit_reply`
records the event with a hardcoded actor type:

```python
await self._log_event(db, review_id, tenant_id, ACTOR_PROVIDER,
                      replied_by_user_id, EVT_REPLY_SUBMITTED, ...)
```

So a customer's text was written into the audit trail **as a provider
action**, and — if the tenant's policy has `require_reply_moderation` off —
published immediately and notified to the reviewing customer via
`notify_customer_review_reply`.

Ownership itself was already checked here (`review.tenant_id != tenant_id →
PERMISSION_DENIED`), so the gap was **persona**, not tenancy. That is why this
route ranked below `flag_review` despite being the one 2F-23's queue named.

## The fix

| Control | After |
|---|---|
| Persona | `require_tenant_owner_mutation` — `tenant_owner` + `super_admin` |
| Mutation scope | read-only `access_scope` denied |
| Ownership | central `_get_review_scoped(tenant_id=<JWT tenant>)` |
| Actor identity | `replied_by_user_id = user.user_id` from the JWT (unchanged, already correct) |
| Actor type | `ACTOR_PROVIDER` — now truthful, because only a provider persona can reach this code |
| Request body | strict `ProviderReplyRequest`, `extra="forbid"`, `reply_text` 1–5000 chars |

The ownership behaviour is preserved but re-expressed through the central
lookup, so a foreign review id is now a SQL non-match (`REVIEW_NOT_FOUND`)
rather than a loaded row plus a manual comparison — consistent with
`flag_review` and privacy-equivalent for missing vs unauthorized.

## Reply text validation

Previously `body["reply_text"]` — a raw `KeyError` (HTTP 500) if absent, and
no length bound. Now schema-validated: required, non-empty, max 5000
characters.

## One reply per review — preserved, not redesigned

The pre-existing uniqueness guard is unchanged:

```python
existing = await db.execute(select(ReviewReply).where(ReviewReply.review_id == review_id))
if existing.scalars().first():
    raise ValueError(ERR_REPLY_ALREADY_EXISTS)
```

- Duplicate reply → `REPLY_ALREADY_EXISTS`, raised **before** any write.
- No edit or replace route exists for a provider reply. Multi-reply semantics
  were **not** invented, per the mission's explicit prohibition. Whether a
  provider may edit a reply within a window is recorded as a product decision.

## Reply state

`submit_reply` sets `pending` or `approved` depending on the tenant's
`require_reply_moderation` policy (default: moderation required). A provider
cannot select the state; it is derived from policy. Admin
`approve_reply`/`reject_reply` remain `require_super_admin`.

## Client-controlled fields rejected

`extra="forbid"` means `tenant_id`, `replied_by_user_id`, `actor_type`,
`status`, `provider_id` and `review_id` in the body are rejected with 422
rather than silently ignored — asserted per-field by
`test_reply_body_rejects_actor_tenant_and_status_fields`.

## Tests
`TestProviderReplyAuthority` (7), including a cross-tenant rejection that
asserts no persistence occurred.
