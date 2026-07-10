# Admin Tenant Detail — Provider 360 Enterprise UI Redesign Report

## Route
`/admin/tenants/[id]` → `frontend/super-admin/app/admin/tenants/[id]/page.tsx`

## Visual Redesign

### Hero Card
- Dark gradient accent strip (brand → indigo → violet) at top
- Glass card with `boxShadow: "0 4px 32px rgba(0,0,0,0.10)"`
- Gradient avatar (brand → indigo) with initial letter fallback
- Larger 80×80px avatar with border-radius 18, shadow
- Tenant name (22px, 800 weight, letter-spacing)
- Subtitle: City, State · Since Month Year
- Status badges row: Status · Plan · Health Band · Bookable/Not Bookable · Verification
- Meta chips: Tenant ID (short, copy button) · Billing Mode · Commission % · Health Score
- Primary actions: Add Usage Credits · Change Plan · Suspend/Reinstate
- More ⋯ dropdown: Approve/Review · Adjust Deposit · Request Changes · Send Notification · Export Report
- Usage Credits mini card (top-right): shows current balance + "+ Add" button

### KPI Cards (8 cards, responsive grid)
1. Usage Credit Balance
2. Credits Deducted Lifetime
3. Security Deposit Held
4. Health Score
5. Staff Members
6. Average Rating
7. Open Complaints
8. Active Jobs

### Tab Navigation (7 groups)
Overview · Setup · Operations · Finance · Trust & Quality · Media · Audit

### Overview Tab (2-column layout)
**Left column:**
- Provider Readiness (circular SVG progress ring + color-coded checklist cards)
- Recent Jobs
- Recent Bookings
- Effective Engines

**Right column:**
- Reviews (large rating number + count)
- Tenant Info (Billing Mode, Commission, Health Band, Activated, short ID)
- Health Signals (labelled progress bars with SIGNAL_LABELS mapping)
- Feature Flags (compact chips)

## Provider Readiness
- `CircularProgress` SVG component: color-coded ring (green=Ready, orange=At Risk, red=Blocked)
- States: Ready · Needs Setup · At Risk · Blocked
- 10 checks with green/red pill cards (clickable to jump to relevant tab)
- Pass count: `X of 10 checks complete`

## Health Signals
Signal key → Display label mapping (`SIGNAL_LABELS` constant):
- `job_completion` → "Job Completion Rate"
- `customer_satisfaction` → "Customer Satisfaction"
- `warranty_claim` / `warranty_claim_rate` → "Warranty Claim Rate"
- `credit_wallet_health` / `usage_credit_health` → "Usage Credit Health"

## Status Labels
`STATUS_LABELS` constant maps all raw enum values to proper display labels.
`labelOf()` helper used throughout.
