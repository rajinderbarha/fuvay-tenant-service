# Finance Presentation Pattern

Showcase: `/dev/ux-02/finance` (`app/dev/ux-02/finance/page.tsx`). Readiness: `MOCK_DESIGN_ONLY`.

## Canonical finance rules honored
- Platform **package credit** (a prepaid balance tenants buy from the platform) is presented
  entirely separately from **ordinary on-site job payments**, which ServiceOS does not process on
  tenants' behalf. No revenue/payment total in this view mixes the two.
- **Commission** is presented as a rate deducted from tenant package credit, not as platform
  revenue collected from job payments.
- **Security deposit** is a separate held amount, not commission-eligible and not combined with
  package credit in any total.
- No payout/withdrawal UI exists anywhere in this phase — consistent with the platform not
  processing job payments.

## Sections
Platform Package Credit (sum across tenants), Security Deposits Held (sum), Commission (per-tenant
rate list).
