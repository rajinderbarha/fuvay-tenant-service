# ServiceOS — Final Performance Report

**Date:** 2026-07-03
**Sprint:** 36 (verification)
**Source:** Sprint 33 (Performance + Load Testing)

---

## Pagination Caps (Applied in Sprint 33)

All list endpoints that previously had no upper bound on `page_size` now enforce a maximum:

| Endpoint Group | Max page_size | Default page_size |
|---------------|---------------|-------------------|
| Invoices | 500 | 25 |
| Payments | 500 | 25 |
| Commissions | 500 | 25 |
| All other list endpoints | 100 | 25 |

Requests with `page_size > max` are clamped to max (not rejected), preventing accidental full-table scans via API.

---

## Database Indexes Added (Migration 048)

Six composite indexes added to the highest-traffic tables:

| Table | Index Columns | Reason |
|-------|--------------|--------|
| `customer_reviews` | `(tenant_id, created_at DESC)` | Tenant review listing, sorted by date |
| `customer_reviews` | `(provider_id, status)` | Provider review status filter |
| `customer_reviews` | `(customer_id, created_at DESC)` | Customer review history |
| `customer_complaints` | `(tenant_id, status, created_at DESC)` | Admin complaint dashboard |
| `customer_complaints` | `(customer_id, created_at DESC)` | Customer complaint history |
| `customer_complaints` | `(assigned_to, status)` | Staff complaint queue |

All indexes use B-tree (default); partial indexes not used as status values change frequently.

---

## Load Testing Results (Sprint 33)

| Scenario | Concurrent Users | RPS | P95 Latency | Result |
|----------|-----------------|-----|-------------|--------|
| GET /v1/provider/service-jobs (paginated) | 50 | 120 | 180ms | PASS |
| POST /v1/auth/login | 20 | 40 | 220ms | PASS |
| GET /v1/admin/analytics/summary | 10 | 15 | 340ms | PASS |
| POST /v1/customer/ai/chat (with tool calls) | 5 | 8 | 1,200ms | PASS (AI latency expected) |

*Tests run against local PostgreSQL with connection pool size 20. Production managed DB expected to perform better.*

---

## Connection Pool Configuration

```python
DATABASE_POOL_SIZE: int = 20
DATABASE_MAX_OVERFLOW: int = 10
DATABASE_POOL_TIMEOUT: int = 30
```

Under load of 50 concurrent requests, no pool exhaustion observed. `max_overflow=10` provides burst capacity to 30 total connections.

---

## Redis Cache

- `REDIS_CACHE_TTL_SECONDS: int = 300` (5 minutes)
- Engine registry cached for `ENGINE_REGISTRY_CACHE_TTL: int = 300` seconds
- OTP sessions stored with TTL (`OTP_TTL_SECONDS`)
- Booking slot holds stored with TTL; expire_drafts job cleans up every 15 minutes

---

## Known Performance Gaps

1. **RAG/embedding** — not load-tested; embedding calls are synchronous within async handler
2. **AI chat under high concurrency** — DeepSeek API rate limits not yet characterized
3. **Full-text search** — not implemented; filtering is index-range based
4. **Background job throughput** — notification dispatch not benchmarked; runs every 1 minute

---

## Performance Tests (Sprint 33)

36 test functions added covering:
- Pagination cap enforcement (page_size > max returns capped result, not error)
- Index presence (via `information_schema.statistics` queries in migration)
- Response time assertions for key endpoints under simulated concurrent load
