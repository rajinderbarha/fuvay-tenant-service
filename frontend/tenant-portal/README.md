# ServiceOS — Tenant Owner Portal

Next.js 15 dashboard for service business owners.

## Pages (14)

| Route | Description |
|---|---|
| /login | Stores 6 context keys in localStorage |
| /dashboard | Jobs-first layout, KPIs, SLA alerts |
| /jobs | Filter/search with SLA badge |
| /jobs/[id] | Status transitions (VALID_TRANSITIONS graph), history |
| /bookings | Confirm / reject / convert to job |
| /staff | List + DS performance scores |
| /staff/[id] | Performance breakdown, schedule edit |
| /customers | Health band tabs, search |
| /customers/[id] | Health signals, risk flags, job history |
| /finance | Wallet, commissions, payout request |
| /reviews | One-reply enforcement, aggregate |
| /chat | Rooms + messages |
| /documents | Sign now, generate, status tabs |
| /settings | 3-tier source display, webhooks |

## Running

```bash
npm install
npm run dev     # → http://localhost:3001
```

## Tests

```bash
python -m pytest tests/test_tenant_portal.py -v   # 34 tests
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
