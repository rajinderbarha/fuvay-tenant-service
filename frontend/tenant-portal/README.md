# Fuvay — Tenant Owner Portal

Next.js dashboard for service business owners.

## Canonical Home Services workspaces

| Route | Description |
|---|---|
| /login | Stores 6 context keys in localStorage |
| /dashboard | Live operations, capacity, quality and finance summary |
| /home-services/bookings-jobs | Booking-to-job pipeline and job detail drawer |
| /home-services/dispatch | Assignment and dispatch |
| /home-services/availability | Provider and technician capacity |
| /home-services/services | Admin-catalog services, options and tenant pricing |
| /home-services/team | Team, skills and operational readiness |
| /business/coverage-hours | Zipcode coverage, hours and booking controls |
| /inventory | Tenant-owned parts inventory |
| /customers | Health band tabs, search |
| /customers/[id] | Health signals, risk flags, job history |
| /home-services/reviews | Reviews and provider replies |
| /home-services/complaints | Provider/customer complaint workflow |
| /provider/refund-requests | Provider-owned refund and warranty remedies |
| /home-services/finance | Usage credits, top-up plans and deductions |

## Running

```bash
npm install
npm run dev     # → http://localhost:3001
```

## Tests

```bash
python -m pytest tests/test_tenant_portal.py -v
```

## Connecting to Backend

```bash
# 1. Copy env file
cp .env.local.example .env.local

# 2. Edit .env.local
NEXT_PUBLIC_API_URL=http://localhost:8000   # default works if backend on same machine

# 3. Start backend first, then portal
cd ../../ && uvicorn app.main:app --reload
cd frontend/tenant-portal && npm run dev
```

Runs at **http://localhost:3001**. Backend must be running on `localhost:8000`.
