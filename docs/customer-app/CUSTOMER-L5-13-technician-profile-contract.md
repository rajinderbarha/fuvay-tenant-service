# CUSTOMER-L5-13 — Technician Profile Contract

## Decisive Finding: No Customer-Facing Technician Profile Exists

Exhaustively verified this sprint (own research + independent
cross-check, both reaching the same conclusion): `ProviderTeamMember`
(`app/engines/home_service_assignment/staff_model.py`) is the real
technician/staff model, with real columns `full_name`, `profile_photo_url`,
`skills` (JSONB), `designation`, `status` — but **zero customer-facing
endpoints anywhere in this backend join to this table**. The only
technician-related data any customer-facing router ever returns is a bare
`assigned_staff_id` UUID (never resolved to a name) or generic,
role-level event labels (e.g., "Technician assigned.").

## Field-by-Field Classification (per §10's requested field list)

| Spec-requested field | Real backend equivalent | Classification |
|---|---|---|
| `display_name`/`first_name` | `ProviderTeamMember.full_name` exists in the DB, but no customer endpoint returns it | `MISSING_BACKEND` (column exists, not exposed) |
| `profile_photo` | `ProviderTeamMember.profile_photo_url` exists in the DB — **not even included in the model's own `to_dict()`** (confirmed by direct reading) | `MISSING_BACKEND` |
| `verification_status` | No such column exists on `ProviderTeamMember` at all | `MISSING_BACKEND` |
| `badges` | No such column/table exists for technicians (only the tenant/business-level `public_badges` already used since CUSTOMER-L5-08) | `MISSING_BACKEND` |
| `rating_average`/`rating_count` | `StaffRatingSummary` (`app/engines/customer_reviews/models.py`) is a real, computed aggregate — but exposed only via admin/provider routers, never customer-facing | `MISSING_BACKEND` (computed, not exposed) |
| `experience_summary`/`completed_jobs` | No such fields exist anywhere | `MISSING_BACKEND` |
| `skills`/`languages` | `ProviderTeamMember.skills` (JSONB) exists in the DB, `languages` does not exist as a column at all — neither is customer-reachable | `MISSING_BACKEND` |
| `service_specializations`/`brand_specializations` | `ProviderTeamMember.supported_offering_ids`/`supported_type_ids`/`supported_brand_ids` exist in the DB, not customer-reachable | `MISSING_BACKEND` |
| `customer_visible_contact_actions` | No masked-call/contact system exists anywhere | `MISSING_BACKEND` |

## Consequence

This sprint builds **no** technician-profile summary or detail screen
(§11/§12) — there is no real data anywhere to render, and every field the
spec requests is either a DB column with no customer-facing endpoint, or
does not exist at all. Building a profile screen with a fabricated name,
photo, or rating would be a direct violation of this project's central,
repeatedly-enforced discipline (see `known-gaps.md` for the full,
itemized disclosure). The customer-facing experience remains exactly what
CUSTOMER-L5-08/L5-11/L5-12 already established: a **business/Tenant-level**
provider summary (`provider_name`, `rating`, `public_badges` — all real,
already customer-safe), never an individual technician's identity.

## What Would Close This Gap (Not This Sprint's Scope)

A real backend change — a new customer-facing endpoint joining
`ServiceJob.assigned_staff_id` → `ProviderTeamMember` (returning at minimum
`full_name`/`profile_photo_url`), and separately, a new endpoint exposing
`StaffRatingSummary` for a specific technician. Neither exists today; this
sprint documents the gap precisely rather than building around it with
invented data.
