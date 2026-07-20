# CUSTOMER-L5-02 — Profile Contract

Field classification of `app/engines/auth/service.py#_user_to_profile` (the
only customer identity model this backend has — see
`CUSTOMER-L5-03-backend-contract-audit.md` for the note that there is no
separate "customer" table, just `User.role == "customer"`).

| Field | Classification | Notes |
|---|---|---|
| `user_id` / `id` | READ_ONLY | Identical values, both present in the real response |
| `email` | READ_ONLY (this sprint) | Editable field exists in `UpdateProfileRequest`? No — the backend's `UpdateProfileRequest` schema (`schemas.py`) only accepts `full_name`, `phone`, `avatar_url`. Email is not updatable via `PUT /v1/auth/me`. |
| `phone` | EDITABLE (backend), READ_ONLY (this client) | Backend's `UpdateProfileRequest.phone` accepts a new phone directly with **no OTP re-verification step** — i.e. the real backend does *not* enforce contact-change re-verification for phone. CUSTOMER-L5-02 §30 requires the client to treat contact changes as needing re-verification when the backend requires it; since the backend does not, allowing direct phone edit through the generic profile endpoint would be a real account-security weakness the client should not amplify. This client renders phone as **read-only** rather than exploiting the backend's lack of re-verification — a deliberate client-side security posture stricter than the bare minimum the backend enforces. |
| `full_name` | EDITABLE, REQUIRED | Backend: `min_length=2, max_length=255`. Client (`AppTextField`) mirrors the 2-char minimum. |
| `display_name` | READ_ONLY | Present in the response (`getattr(user, "display_name", None)`), not in `UpdateProfileRequest` — not backend-editable. |
| `avatar_url` | EDITABLE | Backend-editable via `UpdateProfileRequest.avatar_url`; **not surfaced in this sprint's UI** — no image-picker/upload flow was built (see known-gaps; `AppAvatar`'s `imageUrl` prop reads it but nothing writes it). |
| `preferred_language` | MISSING_BACKEND (as a distinct field) | The response has `language` (default `"en"`), not `preferred_language`; not present in `UpdateProfileRequest` — **not backend-syncable**. This sprint's language preference (CUSTOMER-L5-00 i18next) remains device-local only, per `CUSTOMER-L5-02-known-gaps.md`. |
| `preferred_theme` | MISSING_BACKEND | No such field anywhere in this contract. Theme preference (CUSTOMER-L5-00) is and remains device-local only — correct per the sprint brief's own allowance ("local persistence... backend preference sync only where supported"). |
| `timezone` | READ_ONLY | Present, not editable via this endpoint. |
| `role` | READ_ONLY, DERIVED | Always `"customer"` for accounts created via `/register/customer`. |
| `tenant_id` | READ_ONLY | Marketplace/tenant binding — see security review. |
| `is_verified` | READ_ONLY, DERIVED | Set `true` automatically on first successful OTP verify. |
| `is_mfa_enabled` | READ_ONLY (this sprint) | Real field; MFA setup flow not built for customers this sprint (see contract matrix — UNVERIFIED for customer use). |
| `is_active` | READ_ONLY, DERIVED | Drives the `disabled`-account failure case (see failure matrix). |
| `onboarding_complete` | READ_ONLY (this client), DERIVED (backend) | Mapped into `CustomerSession.onboardingComplete`; no client-side onboarding-completion calculation exists — matches CUSTOMER-L5-01 §33's instruction not to compute completeness from frontend assumptions when the backend provides a status. |
| `force_password_change` / `password_reset_required` / `temporary_password_active` | NOT_APPLICABLE | Password-path-only fields; irrelevant to the OTP-only customer flow this sprint implements. |
| `password_changed_at` | NOT_APPLICABLE | Same reason. |
| `profile_photo_media_id` | READ_ONLY | Present, not used this sprint (no media-upload integration). |
| `last_login_at` / `created_at` | READ_ONLY, DERIVED | Present, not surfaced in the UI this sprint. |
| `permissions` | READ_ONLY, DERIVED | Role-based permission list (`ROLE_PERMISSIONS`); not relevant to a customer's own profile screen (this is an RBAC list for staff/admin roles in the shared engine) — not displayed. |

## Consent / Privacy

**MISSING_BACKEND** in full: no consent field exists anywhere in
`_user_to_profile`, no consent endpoint exists in `router.py`. CUSTOMER-L5-02
§17's consent requirements (terms/privacy/marketing, versioned,
timestamped, auditable) cannot be implemented against this backend as it
exists today — not attempted, not faked. `RegisterCustomerRequest` also has
no consent fields. This is a real, documented backend gap, not a scope
decision.

## Account Deletion

**MISSING_BACKEND** in full: no deletion/deactivation endpoint exists.
CUSTOMER-L5-02 §38 is explicit that "the UI must explain... use the real
contract" and "do not invent instant deletion" — since there is no real
contract, no account-deletion UI was built this sprint. Documented as a
gap, not a stub screen.
