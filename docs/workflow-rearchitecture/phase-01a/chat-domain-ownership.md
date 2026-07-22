# Decision 4 — Chat and Communication Domain Ownership

## Correction to Phase 1 assumption
Phase 1 inferred `platform_notifications` was "the de facto winner" for chat based on partial evidence. A full per-app grep (SOURCE_VERIFIED, file:line) shows a more fragmented reality — communication is split into 5 domains as instructed, but two domains each still have 2 live competing engines, not a clean single winner.

## Domain 1: Core customer/tenant messaging (rooms/conversations)
- **Live calls:** `mobile/customer-app/src/lib/api.ts:144-149` → `/v1/chat/rooms*` (core `chat` engine). `frontend/tenant-portal/lib/api.ts:901-915` → `/v1/chat/conversations*` (same core `chat` engine, different resource name).
- **Marking: CANONICAL_FOR_DOMAIN — core `chat/router.py`.** This reverses Phase 1's inference; the generic chat engine is not dead, it is the actual backing for customer-facing and tenant-facing core messaging in two separate apps.
- **Thread model:** room/conversation, participants customer + tenant-side user.
- **Record linkage:** UNVERIFIED whether tied to `ServiceJob`/booking — needs confirmation before the Booking Exception workspace's "Contact customer" action can be wired to this domain with confidence.

## Domain 2: Staff/technician ↔ customer messaging
- **Live calls:** `frontend/tenant-portal/lib/api.ts:3964-3971` → `/v1/staff/chat/threads*`. `mobile/staff-app/src/lib/api.ts:233-239` → `/v1/staff/chat/threads*`, with an explicit code comment (`:107-109,231`) stating the app used to incorrectly call the generic `/v1/chat/rooms/*` and was deliberately rewired to `/v1/staff/chat/*`.
- **Marking: CANONICAL_FOR_DOMAIN — `platform_notifications` staff_chat_router.** This is the one domain where Phase 1's inference is directly confirmed by both a second app's usage and an explicit in-code correction comment — the strongest evidence of any domain in this decision.
- **Thread model:** thread linked to assigned job (technician-customer or technician-tenant).

## Domain 3: Provider (tenant-owner) ↔ customer/staff messaging
- **Live calls:** `frontend/tenant-portal/lib/api.ts:3478-3488` → `/v1/provider/chat/threads*`.
- **Marking: CANONICAL_FOR_DOMAIN — `platform_notifications` provider_chat_router**, consistent with Domain 2's engine family.

## Domain 4: Admin support/moderation communication
- **Live calls:** `frontend/super-admin/lib/api.ts:6882-6890` → `/v1/admin/chat/threads*` and `/v1/admin/chat/messages/*`.
- **Marking: CANONICAL_FOR_DOMAIN for this specific surface** — router family not fully disambiguated in this pass (could be core `chat` admin routes or `platform_notifications` admin_chat_router; both are plausible given the `/v1/admin/chat` path style). Recommend a follow-up code-read (not a product decision) to confirm before Phase 2 touches this screen — non-blocking since admin support chat isn't part of the 3 reference workflows.

## Domain 5: Customer ↔ AI booking conversation — **confirmed genuine duplication, unresolved**
- **Live calls, same app:** `mobile/customer-app/src/lib/api.ts:175,274` → `/v1/ai/chat` (simple, `ai_chat` engine) **and** `mobile/customer-app/src/lib/api.ts:310-332` → `/v1/customer/ai-chat/sessions*` (session-based, `ai_conversation` Sprint 15 engine). Also `frontend/tenant-portal/lib/api.ts:1488` → `/v1/ai/chat`. `frontend/super-admin/lib/api.ts:5541-5592` → `/v1/admin/ai-chat/*` (sessions, logs, prompt-templates, test-console — `ai_conversation` admin surface).
- **Marking:** Both `ai_chat` (`/v1/ai/chat`) and `ai_conversation` (`/v1/customer/ai-chat/sessions`) are **simultaneously CANONICAL_FOR_DOMAIN candidates**, actively called by the *same production app* for what appear to be two different AI interaction modes (a quick one-shot assistant vs. a persistent session). This is not dead duplication — it may be two legitimately distinct features that happen to share the label "AI chat." **Requires a product decision, not inferable from code alone**: are these one feature or two? Flagged as genuinely open, non-blocking for Phase 2's 3 reference workflows (none of them require AI chat UI).
- `ai_conversation` Sprint 29 hardening variant: SUPPORTING (extension/hardening of the Sprint 15 engine, not a separate domain).

## Domain 6 (not originally separated, but evidence requires it): AI recommendations
- **Live call:** `frontend/super-admin/lib/api.ts:7996` → `/v1/ai/recommendations` — this is a distinct capability (recommendation_router, part of admin_catalog per Phase 1's router inventory) miscategorized as "chat" only by path prefix similarity. **Not a chat domain at all** — noting here only to prevent it being wrongly folded into Domain 5's resolution.

## Summary marking table

| Engine/path | Domain | Marking | Evidence strength |
|---|---|---|---|
| `chat/router.py` (`/v1/chat/rooms`, `/v1/chat/conversations`) | Core customer/tenant messaging (1) | CANONICAL_FOR_DOMAIN | Strong — 2 apps, confirmed live |
| `platform_notifications` staff_chat_router (`/v1/staff/chat/threads`) | Staff/technician messaging (2) | CANONICAL_FOR_DOMAIN | Strongest — 2 apps + explicit migration comment |
| `platform_notifications` provider_chat_router (`/v1/provider/chat/threads`) | Provider messaging (3) | CANONICAL_FOR_DOMAIN | Strong |
| `/v1/admin/chat/threads` (engine family TBD) | Admin support (4) | CANONICAL_FOR_DOMAIN (surface confirmed, owning engine unconfirmed) | Medium |
| `ai_chat` (`/v1/ai/chat`) | AI booking conversation (5) | CANONICAL_FOR_DOMAIN candidate — **unresolved duplication with ai_conversation** | Strong usage, weak resolution |
| `ai_conversation` Sprint 15 (`/v1/customer/ai-chat/sessions`, `/v1/admin/ai-chat/*`) | AI booking conversation (5) | CANONICAL_FOR_DOMAIN candidate — **unresolved duplication with ai_chat** | Strong usage, weak resolution |
| `ai_conversation` Sprint 29 hardening | AI booking conversation (5) | SUPPORTING | — |
| `notification/router.py` | System notifications | CANONICAL_FOR_DOMAIN | Unchanged from Phase 1 |

## Decision status
**PARTIALLY CLOSED — stronger than Phase 1, but not fully.** Domains 2 and 3 (staff/technician and provider messaging — the ones the 3 reference workflows actually need for "Contact customer"/job-linked chat) are confidently and strongly resolved. Domain 1 is now also resolved (reversing Phase 1's mismarking of `chat/router.py` as legacy — it is live and canonical for customer/tenant core messaging). Domain 5 (AI conversation) has a confirmed, real, simultaneous-use duplication that requires a product decision on whether `ai_chat` and `ai_conversation` are one feature or two — this is explicitly out of scope for Phase 2 since no reference workflow needs AI chat UI, but should not be silently merged by a future engineer without this product input.
