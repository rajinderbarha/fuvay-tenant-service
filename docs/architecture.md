# Fuvay architecture

Fuvay is a multi-tenant service marketplace. A FastAPI application owns
the business rules and PostgreSQL data, while separate web and mobile clients
serve platform administrators, providers, staff, and customers.

## Runtime map

- **Auth Engine** — login, OTP, role and tenant context, signup, business
  approval, and effective permissions.
- **Catalog and serviceability engines** — canonical services and job types,
  provider offerings and prices, zip-code coverage, and bookability gates.
- **Booking Engine** — customer, Instagram, and WhatsApp booking intake,
  address collection, quote/price confirmation, and booking creation.
- **Dispatch Engine** — assignment, availability, technician work, job status,
  evidence, and completion.
- **Finance engines** — provider credits, completion deductions, direct
  payments, refunds, and immutable financial records. The retired security
  deposit model is not part of the current architecture.
- **Complaint, review, trust, and compliance engines** — support requests,
  resolution/refund workflows, ratings, account health, badges, verification,
  consent, and data-rights requests.
- **Notification engines** — in-app, email, WhatsApp, and Instagram delivery,
  preferences, templates, and job/customer messaging.
- **AI Chat Engine** — guided customer assistance and structured support
  intake; authoritative booking and financial writes remain in domain engines.

## Clients

- `frontend/super-admin` — platform operations and business approval.
- `frontend/tenant-portal` — provider setup, services, jobs, finance, quality,
  compliance, and customer care.
- `mobile/customer-app` — booking, job tracking, support, refunds, reviews,
  profile, and notifications.
- `mobile/staff-app` — assigned work, navigation/contact, checklists, evidence,
  completion, and notifications.

Every tenant-owned read or write derives tenant scope from the authenticated
principal. Webhooks translate channel-specific messages into the same domain
services used by the first-party clients; they do not own separate booking or
payment truth.
