# Real Estate Model Lineage — Slice 2F-11 (Workstream 2)

## Models actually present (confirmed by direct source read)

| Model | Table | Classification |
|---|---|---|
| `RealEstateLead` | `real_estate_leads` | CUSTOMER_LEAD_OR_INQUIRY — a lead created from a confirmed intake draft (`draft_id`), carrying `customer_id`, `tenant_id`, `agent_id`, requirement snapshot fields (`budget_min/max`, `rent_min/max`, `city`, `locality`, `property_type` as a free-text/category field, not a normalized property record), and `status`. |
| `RealEstateLeadExecutionEvent` | (execution events table) | AUDIT_OR_HISTORY — one row per status transition, `old_status`/`new_status`/`actor_user_id`/`actor_role`/`notes`. |
| `RealEstateLeadNote` | (lead notes table) | CUSTOMER_LEAD_OR_INQUIRY (a sub-record of the lead) — `is_customer_visible` flag distinguishes internal vs customer-visible notes. |

## Models NOT present (confirmed absent, not assumed)
No `Property`, `PropertyListing`, `PropertyType`, `ListingType`,
`PropertyUnit`, `PropertyMedia`, `PropertyDocument`, `Owner`/`Seller`,
`Inquiry` (distinct from `RealEstateLead`), `ViewingRequest`,
`ViewingAppointment`, `Offer`, `Negotiation`, or `Reservation` model
exists anywhere in this codebase — confirmed by grep across
`app/engines/final_records/models.py` (where `RealEstateLead` and its
siblings live) and the broader `app/` tree. `property_type`/`city`/
`locality`/`zipcode` on `RealEstateLead` are free-text/requirement
fields describing what the customer is looking for, not a normalized,
tenant-managed property listing.

## What "property_type" and location fields actually represent
These fields describe the **customer's stated requirement** (what kind
of property, where) captured at lead-creation time — not a tenant-owned,
publishable property record. There is no publish/unpublish concept, no
availability toggle, and no property-ownership-transfer concept anywhere
in this domain.

## Conclusion: this is a CRM-style lead tracker, not a marketplace
Every one of the mission's anticipated capabilities under "Property
Management," "Media and Documents," "Viewing and Execution" (as a
provider-scheduled site visit against a listing), and "Offer or
Negotiation" (Workstream 3) has **no corresponding model or route** in
this codebase. The only real, existing capability is real-estate LEAD
lifecycle management (accept/reject/contact/follow-up/site-visit-plan/
site-visit-complete/qualify/disqualify/convert/close-lost) plus notes —
all operating on the single `RealEstateLead` record and its 2 child
tables. This is reported honestly, per the mission's explicit
instruction not to assume the module implements the full real-estate
product vision or fabricate documentation for nonexistent capabilities.
