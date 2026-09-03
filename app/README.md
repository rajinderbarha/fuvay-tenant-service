# Fuvay — Backend API

FastAPI + Python 3.12. 26 engines, 15 migrations, RFC 7807 error format, rate limiting, idempotency.

## Running

```bash
pip install -r requirements.txt
alembic upgrade head
uvicorn app.main:app --reload --port 8000
```

## Key Endpoints

| Method | Path | Description |
|---|---|---|
| GET | /health | Liveness + readiness check |
| GET | /metrics | Prometheus metrics |
| POST | /v1/auth/login | Super admin / tenant owner login |
| POST | /v1/auth/staff/login | Staff login |
| POST | /v1/auth/customer/login | Customer email login |
| POST | /v1/auth/customer/otp-request | Request OTP |
| GET | /v1/tenants | List tenants (super admin) |
| POST | /v1/tenants | Create tenant |
| GET | /v1/jobs | List jobs |
| POST | /v1/ai/chat | DeepSeek AI assistant |

## Error Format (RFC 7807)

```json
{
  "error_code": "TENANT_NOT_FOUND",
  "message": "Tenant with ID xxx not found.",
  "resolution": "Check the tenant ID and try again.",
  "request_id": "req_abc123",
  "status": 404
}
```

## Rate Limits

| Endpoint | Limit |
|---|---|
| POST /v1/auth/login | 10 per 15 min per IP |
| POST /v1/auth/customer/otp-request | 3 per hour per phone |
| POST /v1/ai/chat | 20 per hour per customer |
| General API | 200 per min per token |

## Security Headers

All responses include: `X-Content-Type-Options`, `X-Frame-Options: DENY`, `X-XSS-Protection`, `Referrer-Policy`, `Permissions-Policy`, `Strict-Transport-Security` (production only).
