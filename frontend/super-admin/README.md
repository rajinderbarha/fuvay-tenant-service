# Fuvay — Super Admin Portal

Next.js 15 dashboard for platform administrators.

## Pages

| Route | Description |
|---|---|
| /login | JWT authentication |
| /dashboard | Platform KPIs, charts, tenant table |
| /tenants | Tenant list with Onboard Tenant modal, Export CSV |
| /tenants/[id] | 360° view, wallet top-up, suspend/activate |
| /operations | Jobs board, SLA alerts, Reassign Staff modal |
| /operations/[jobId] | Job detail, Override Status, Force Close |
| /finance | Platform revenue, billing config |
| /security | IP blocklist, activity feed, audit log |
| /compliance | DPDP deletion requests, retention policies |
| /marketing | AI-generated posts, social accounts, budget |

## Running

```bash
npm install
npm run dev     # → http://localhost:3000
```

## Environment

```env
NEXT_PUBLIC_API_URL=http://localhost:8000
```

## Tests

```bash
python -m pytest tests/test_super_admin.py -v   # 55 tests
```

## Connecting to Backend

```bash
# 1. Copy env file
cp .env.local.example .env.local

# 2. Edit .env.local
NEXT_PUBLIC_API_URL=http://localhost:8000   # default works if backend on same machine

# 3. Start backend first, then portal
cd ../../ && uvicorn app.main:app --reload
cd frontend/super-admin && npm run dev
```

Runs at **http://localhost:3000**. Backend must be running on `localhost:8000`.
