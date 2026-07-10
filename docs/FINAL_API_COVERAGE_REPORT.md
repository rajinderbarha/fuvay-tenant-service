# ServiceOS — Final API Coverage Report

**Date:** 2026-07-03
**OpenAPI:** Available at `/docs` and `/openapi.json` when server is running
**Registered routers in main.py:** 39
**Version prefix:** `/v1`

---

## API Surface by Role

### Super Admin APIs
| Tag / Area | Prefix | Key Endpoints |
|-----------|--------|---------------|
| Auth | /v1/auth | login, refresh, logout, me |
| Tenants | /v1/admin/tenants | CRUD, approve, suspend |
| Users | /v1/admin/users | CRUD, password reset |
| Engines | /v1/admin/engines | list, enable, disable, health-history |
| Service Catalog | /v1/admin/catalog | categories, services, brands, types |
| Pricing | /v1/admin/pricing | tier pricing, brand/type pricing |
| Analytics | /v1/admin/analytics | summary, revenue, bookings, providers |
| Marketing | /v1/admin/marketing | campaigns, templates, automation |
| AI Conversation | /v1/admin/ai | conversation config, hardening |
| Customer Flow | /v1/admin/customer-flow | category flow configs |
| Geo | /v1/admin/geo | zones, districts, areas |
| Dispatch | /v1/admin/dispatch | assignment queue, bulk assign |
| Packages | /v1/admin/packages | package CRUD |
| Audit Logs | /v1/admin/audit | log listing, filter |
| Enterprise Grid | /v1/admin/grid | saved views, column prefs, export |
| Provider Verification | /v1/admin/providers | verify, reject, document review |

### Tenant Owner / Provider APIs
| Tag / Area | Prefix | Key Endpoints |
|-----------|--------|---------------|
| Service Jobs | /v1/provider/service-jobs | list, detail, status transitions |
| Invoices | /v1/provider/service-invoices | list, detail, mark-paid |
| Staff | /v1/provider/staff | CRUD, schedule, availability |
| Onboarding Checklist | /v1/provider/checklist | status, submit, evaluate |
| Offering Enablement | /v1/provider/offerings | enable, disable, price override |
| Provider Registration | /v1/provider/registration | submit, documents, status |
| Area Management | /v1/provider/areas | assign, coverage |
| Reviews | /v1/provider/reviews | list, reply |
| Complaints | /v1/provider/complaints | list, respond |
| Refund Requests | /v1/provider/refund-requests | list, process |
| Wallet | /v1/provider/wallet | balance, transactions, withdraw |
| Marketing | /v1/provider/marketing | campaigns, assets, schedule |
| Analytics | /v1/provider/analytics | revenue, bookings, ratings |
| Subscription | /v1/provider/subscription | current plan, upgrade |
| Sidebar Config | /v1/provider/sidebar | modules, reorder |

### Customer APIs
| Tag / Area | Prefix | Key Endpoints |
|-----------|--------|---------------|
| Bookings | /v1/customer/bookings | list, detail, cancel |
| AI Chat | /v1/customer/ai | chat, meta |
| Flow | /v1/customer/flow | category routing, config |
| Reviews | /v1/customer/reviews | submit, list own |
| Complaints | /v1/customer/complaints | submit, list, withdraw |
| Invoices | /v1/customer/invoices | list, detail, pay |
| Profile | /v1/customer/profile | view, update |

### Public APIs (No Auth)
| Tag / Area | Prefix | Key Endpoints |
|-----------|--------|---------------|
| Registration | /v1/public/register | initiate, confirm-plan, verify, payment-order, complete, webhook |
| Health | /health, /v1/health, /v1/ready | health check, readiness |

---

## Router Count by Category

| Category | Router Count |
|----------|-------------|
| Admin | ~15 routers |
| Provider/Tenant | ~12 routers |
| Customer | ~7 routers |
| Public + Health | ~5 routers |
| **Total registered** | **39** |

---

## Notable API Design Patterns

- All paginated lists use `?page=1&page_size=25` (consistent across all endpoints)
- All list responses return `{items: [...], total: int, page: int, page_size: int}`
- Mutations return the updated resource
- Error responses follow `{detail: "message"}` (FastAPI default)
- Status transitions use explicit action endpoints (e.g., `POST /service-jobs/{id}/start`) rather than PATCH with status field

---

## OpenAPI Documentation

The full OpenAPI schema is available at runtime:
- **Swagger UI:** `http://localhost:8000/docs`
- **ReDoc:** `http://localhost:8000/redoc`
- **JSON Schema:** `http://localhost:8000/openapi.json`

All endpoints have:
- Summary string
- Response schema (Pydantic model)
- Request body schema where applicable
- Authentication requirement noted
