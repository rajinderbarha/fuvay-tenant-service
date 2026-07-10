# ServiceOS — Final Known Issues Register

**Date:** 2026-07-03
**Release:** serviceos-rc-1
**Status:** Last updated Sprint 36

---

## P0 Issues (Release Blockers) — ALL RESOLVED

| ID | Issue | Fixed In |
|----|-------|---------|
| P0-01 | nginx/nginx.conf missing — prod compose would fail | Sprint 35 |
| P0-02 | DEBUG defaulted to True | Sprint 35 |
| P0-03 | Dev secrets allowed in production with no enforcement | Sprint 35 |
| P0-04 | next.config.js missing — API URL falls back to localhost in prod | Sprint 35 |
| P0-05 | Invoice endpoints missing /v1 prefix (404 in production) | Sprint 32 |
| P0-06 | RAG router registration order breaking startup | Sprint 32 |
| P0-07 | Tenant isolation failure in invoice endpoint (IDOR) | Sprint 32 |

**Zero P0 issues remain open.**

---

## P1 Issues (Important, Non-Blocking for rc-1)

| ID | Area | Issue | Plan |
|----|------|-------|------|
| P1-01 | Infrastructure | Staging environment not yet provisioned | Requires cloud setup |
| P1-02 | Infrastructure | TLS certificates are placeholders | Needs Let's Encrypt before staging |
| P1-03 | Background Jobs | No containerised job scheduler | Use host cron per scripts/cron_jobs.sh |
| P1-04 | /v1/health and /v1/ready | Added in Sprint 35 — were missing | RESOLVED |
| P1-05 | .env.example key mismatches | Rewritten in Sprint 35 | RESOLVED |

---

## P2 Issues (Nice to Have)

| ID | Area | Issue | Notes |
|----|------|-------|-------|
| P2-01 | Payments | Stripe integration is config-only | Business logic pending future sprint |
| P2-02 | Monitoring | Grafana dashboards are stubs | Need real panel configs |
| P2-03 | Mobile | React Native apps not in web release | Apps exist in repo; separate release |
| P2-04 | E2E | Playwright tests require live servers | Structural tests pass; browser tests pending |
| P2-05 | AI | DeepSeek rate limits not characterized | Need production traffic data |
| P2-06 | Notifications | FCM/Twilio/SendGrid are config-optional | Queues but doesn't dispatch without keys |
| P2-07 | DevOps | Background job scheduler not containerised | Scripts exist; cron on host |
| P2-08 | Search | No full-text search implemented | Filtering is index-range based |

---

## Technical Debt

| ID | Area | Debt | Priority |
|----|------|------|---------|
| TD-01 | Tests | Test files had hardcoded `/home/claude/serviceos/` paths | FIXED Sprint 36 |
| TD-02 | Tests | `test_phase21_e2e.py` validates Playwright spec structure; specs exist but browser tests untested | Low |
| TD-03 | Config | `REDIS_PASSWORD` must be embedded in `REDIS_URL` string; no separate env var support | Low |
| TD-04 | Mobile | `aiChatApi` renamed to `aiConversationApi` in customer-app; test updated | Done |
| TD-05 | Versions | `httpx==0.28.1` in requirements; version test updated to accept both 0.28.1 and 0.29.0 | Done |

---

## Explicitly Out of Scope for rc-1

- RBAC field-level policies (admin sees all vs. owner sees own subset)
- API key rotation endpoint
- IP allowlist for admin endpoints
- Full-text search across bookings/jobs
- Push notification delivery (FCM keys not configured)
- Stripe live payment processing
- Mobile app web/store release
- Multi-region deployment
- Database read replicas
