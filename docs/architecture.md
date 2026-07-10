# ServiceOS — Architecture Reference

## Engine Dependency Map

```
Auth Engine
  └─ Provides: JWT, OTP, session management
  └─ Used by: ALL engines (via dependency injection)

Tenant Engine
  └─ Provides: tenant lifecycle, onboarding, engine activation
  └─ Depends on: Auth, Settings, Billing Router

Platform Commerce Engine
  └─ Provides: wallet, commissions, payouts, customer health
  └─ Depends on: Tenant, Payment

Billing Router Engine
  └─ Provides: plan routing (commission vs subscription), invoice generation
  └─ Depends on: Platform Commerce, Subscription, Pricing

Pricing Engine
  └─ Provides: multi-rule price pipeline, surcharges, discounts, tax
  └─ Depends on: Tenant (for vertical rules), Settings

Booking Engine
  └─ Provides: booking CRUD, preflight checks, slot management
  └─ Depends on: Pricing, Auth, Notification

Appointment Engine
  └─ Provides: appointment scheduling with calendar integration
  └─ Depends on: Booking, Notification

Field Ops Engine
  └─ Provides: job lifecycle (23 statuses), VALID_TRANSITIONS, SLA
  └─ Depends on: Booking, Dispatch, Geo, Notification

Dispatch Engine
  └─ Provides: ML-based staff assignment scoring
  └─ Depends on: Field Ops, Data Science, Geo

Geo Engine
  └─ Provides: staff GPS tracking, geofencing, ETA
  └─ Depends on: Field Ops

Data Science Engine
  └─ Provides: churn prediction, demand forecast, staff performance scores
  └─ Depends on: Analytics, Field Ops, Platform Commerce

Analytics Engine
  └─ Provides: platform KPIs, tenant KPIs, chart data
  └─ Depends on: Field Ops, Platform Commerce, Booking

Chat Engine
  └─ Provides: real-time messaging, rooms, read receipts
  └─ Depends on: Auth, Notification

AI Chat Engine
  └─ Provides: DeepSeek LLM with tool calling (customer-facing)
  └─ Depends on: Booking, Field Ops, Pricing, Chat

RAG Engine
  └─ Provides: knowledge base, document embedding, semantic search
  └─ Depends on: Media

Review Engine
  └─ Provides: composite scores, reply management, fraud detection
  └─ Depends on: Field Ops, Notification

Marketing Engine
  └─ Provides: social post scheduling, AI image generation, budget tracking
  └─ Depends on: Media, Notification

Security Engine
  └─ Provides: threat detection, IP blocklist, audit logs, rate limiting
  └─ Used by: Auth, ALL routers (via middleware)

Compliance Engine
  └─ Provides: DPDP deletion requests, retention policies, consent
  └─ Depends on: Auth, Tenant

Notification Engine
  └─ Provides: push, SMS, email (multi-channel), templating
  └─ Depends on: Auth

Document Engine
  └─ Provides: contract generation, e-signing, storage
  └─ Depends on: Booking, Media

Payment Engine
  └─ Provides: Razorpay integration, payout requests, invoice
  └─ Depends on: Platform Commerce, Billing Router

Inventory Engine
  └─ Provides: parts/materials tracking, low-stock alerts
  └─ Depends on: Field Ops

Settings Engine
  └─ Provides: 3-tier config (platform → vertical plan → tenant override)
  └─ Depends on: Tenant

Subscription Engine
  └─ Provides: plan management, usage quotas, upgrades
  └─ Depends on: Billing Router, Payment

Webhook Engine
  └─ Provides: outbound webhooks with retry, HMAC signing
  └─ Depends on: ALL engines (subscriber pattern)
```

## Data Flow — Booking to Completion

```
1. Customer books → Booking Engine (preflight: capacity, pricing, KYC)
2. Booking confirmed → Pricing Engine (multi-rule pipeline: base + surcharges + tax)
3. Job created → Field Ops Engine (status: pending_assignment)
4. Dispatch Engine scores staff → assigns best match
5. Staff accepts → Field Ops (accepted → en_route → arrived → in_progress)
6. GPS updates → Geo Engine (30s interval)
7. Job completes → Field Ops (completed → invoiced)
8. Payment received → Payment Engine → Platform Commerce (commission deducted)
9. Review submitted → Review Engine (composite score + fraud check)
10. Webhook fired → Tenant's endpoint (job.completed event)
```

## Database

- **PostgreSQL 16** with pgvector extension (RAG embeddings)
- **15 Alembic migrations** — sequential, tested
- All tenant data is scoped by `tenant_id` at the row level
- No cross-tenant data leakage possible via ORM layer

## Caching (Redis)

| Key Pattern | TTL | Purpose |
|---|---|---|
| `rate:*` | Sliding window | Rate limiting |
| `idempotency:*` | 24h | Idempotency replay |
| `session:*` | JWT expiry | Session blacklist |
| `kb:*` | 1h | RAG knowledge base cache |
| `health:*` | 30s | Health check cache |

## Security Architecture

```
Request
  → RequestIDMiddleware (assign X-Request-ID)
  → StructuredLoggingMiddleware (bind context)
  → SecurityHeadersMiddleware (OWASP headers)
  → CORSMiddleware (origin validation)
  → IdempotencyMiddleware (replay detection)
  → JWT Validation (in route dependency)
  → Permission Check (P.xxx decorators)
  → Rate Limit Check (Redis sliding window)
  → Business Logic
  → Audit Log (for high-risk operations)
```
