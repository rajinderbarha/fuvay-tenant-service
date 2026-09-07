# Catalog setup and release

## Admin setup order

1. Categories: organize the customer-facing service catalog.
2. Service groups: group related services inside their category.
3. Master services: define service identity and link its supported job types.
4. Types and brands: configure the applicable choices, where relevant.
5. Checklist library: author reusable content and publish the version to be used.
6. Blueprint workspace: configure each active job type in this order: overview, workflow, dimensions, problems/questions, options/add-ons, checklist mappings, tenant rules, review/publishing.

Optional dimensions, add-ons, and checklists should only be enabled when the service needs them. Admin owns structure and permissions; the provider owns prices, supported choices, technician capacity, and availability.

## How publication works now

Save each tab and finish every active job type before selecting **Publish reviewed blueprint** under **Review & Publishing**. The server rejects incomplete readiness checks, invalid workflow steps/capabilities, missing required checklists, and unpublished mapped checklist versions. The error lists the blockers.

A release stores the service configuration, job-type workflows, dimensions/values, questions/options/rules, problem and add-on mappings/definitions, type/brand mappings/definitions, and mapped checklist versions/content. Provider-owned prices are not part of the admin release. Publishing records a new version; provider setup and approval remain separate.

**Important: this is a validated release record, not staged publication.** Individual configuration saves still affect the live catalog. A full unpublished draft → atomic go-live mechanism across every consumer remains outstanding. Existing workflow-bound bookings retain their saved workflow/pricing behavior; this does not mean every catalog field is frozen for an unfinished draft.

## Customer add-on API

After provider matching, authenticated customers can use:

- `GET /v1/customer/home-services/booking-drafts/{draft_id}/addons`
- `PUT /v1/customer/home-services/booking-drafts/{draft_id}/addons` with `{"selections":[{"mapping_id":"UUID","quantity":2}]}`. An empty array removes the selections.

Use the **mapping ID**, not the option-template ID. The server checks exact service/job type, provider support and validity dates, actor permissions, quantity bounds, and provider-owned price. Client price fields cannot set the charge. Nonpriced options remain free. Price ranges are not silently converted to a fixed charge; they need a provider-authored estimate.

Selection returns a recomputed `price_snapshot` and `requires_price_confirmation`. Show `addon_lines` and the updated total, then confirm the standard price again before booking. Changes invalidate the previous price acceptance. Confirmation/finalization rechecks selected add-ons and rejects changed prices. Final bookings retain the selected lines in their frozen price snapshot.

`service_option_ids_json` is the existing multiple-problem-selection field. It is deliberately not interpreted as billable add-ons.

Inspection-first jobs do not accept upfront add-on charges through this API. Their extras belong in the customer-approved estimate.

## Technician add-ons

The web staff job-detail page has a Catalog add-ons section after inspection. It uses:

- `GET /v1/staff/service-jobs/{job_id}/catalog-addons`
- `POST /v1/staff/service-jobs/{job_id}/catalog-addons` with `quote_id`, `mapping_id`, and integer `quantity`.

Only the assigned technician can select permitted post-inspection options for that job. The estimate must belong to the same provider/job and be current, unlocked, and editable. Repeat submissions of the same mapping are rejected. Server-resolved prices become quote items; the existing provider/customer approval process still applies. Selecting an add-on does not directly charge the customer or authorize work.

## Verification and remaining work

Local isolated tests cover dimension inheritance, required fields, saved workflow pricing, add-on prices and quantities, repeat submissions, estimate boundaries, and release manifests. Admin navigation tests and both portal typechecks also pass. These checks do not constitute live end-to-end acceptance.

The native customer/technician application source is not present in this workspace. The customer add-on picker must be connected to the API in that application, and its review/approval screens verified there. The web staff selector is implemented here.

## Instagram and WhatsApp

Both deterministic chat flows now load required fields from the shared blueprint resolver. Workflows that do not require scheduling skip the slot picker. Provider-priced add-ons are offered after the service/address/slot and applicable identity checks, before final confirmation. Customers can add, change quantity, remove, or decline extras. The updated total requires acceptance; final review lists selected extras and provides an Edit add-ons action. Inspection extras still use the existing quote-approval flow.

Add-on actions are bound to the conversation's draft/session and the displayed selection/price revision. Old buttons cannot increment quantities twice or apply to another booking. A changed provider price is re-estimated and displayed for acceptance. Unreviewed selections block final confirmation. Long message summaries are split into messages instead of being truncated; action buttons are withheld if the preceding text failed to send.

The corrected live diagnostic is explicitly opt-in (`RUN_LIVE_CATALOG_DIAGNOSTICS=1`) and uses the configured database and current published/bookable catalog. A read-only check during implementation found 29 active master services and 112 active problem mappings, but **zero enabled/published provider services** in this environment. This is not evidence that the remote deployment has the same data. No provider approvals, publishing records, real messages, or bookings were created by this work.

Local messaging regression tests pass. Deployment, a published/bookable test provider, and controlled Instagram/WhatsApp messages are still required for live end-to-end acceptance.

Before deployment acceptance, run a controlled test booking covering fixed-price add-ons, price-change rejection, an inspection estimate, customer approval, final invoice/payment, and checklist completion. Verify tenant setup/version-review behavior after a catalog release. Do not use real customer bookings or live payments for these checks.
