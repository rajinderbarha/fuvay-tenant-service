# Long-Term Target: TENANT_LOCAL_CUSTOMER_DIRECTORY_WITH_VERIFIED_LINKING

## Status: explicitly out of scope, not begun

Per the ratified product decision, the future target capability is a tenant-local customer
directory with verified linking — allowing a tenant to establish a legitimate first-contact
relationship with a new customer (e.g. via invitation or verified OTP) without requiring a prior
Booking.

## What was explicitly NOT built this slice (per the ratified decision and mission's out-of-scope list)

- No customer-contact table.
- No invitation flow.
- No OTP or consent workflow.
- No customer-directory UI.
- No migration of any kind.

## Interim behavior until this capability exists

First-time customers without an existing same-tenant Booking or Job must enter through the
customer Booking flow (which itself establishes the relationship this slice's guard checks for)
before a tenant can manually create a standalone Job referencing them directly. This is
documented, not silently limiting — see supported-creation-mode-policy.md and
product-decisions-required.md item 2.
