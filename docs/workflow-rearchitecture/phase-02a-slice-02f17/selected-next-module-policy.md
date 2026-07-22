# Selected Next Module — Policy Notes (for the implementation slice)

These are OBSERVATIONS to inform the future implementation slice's own mission — not decisions made or implemented by this discovery slice.

## Inferred persona split
- `provider_*` routes (`provider_chat_router`, `provider_notif_router`): likely `tenant_owner`/`staff`/`super_admin` — i.e. `require_owner_or_office_staff_mutation`, matching the exact precedent from `quote_checklist` (Slice 2F-16), since no technician caller evidence has been confirmed (would need to be checked during implementation, not assumed here).
- `staff_*` routes (`staff_chat_router`, `staff_notif_router`): likely `staff`/`technician`/`tenant_owner`/`super_admin` — i.e. `require_staff_or_above_mutation`, since these are explicitly named "staff" routes and technician involvement in workplace chat/notifications is plausible (unlike quote administration) — but this must be confirmed with frontend/mobile caller evidence during implementation, not assumed.

## Object ownership to investigate during implementation
- Does `provider_send_message`/`staff_send_message` verify the caller is a MEMBER of the target thread before allowing a message write?
- Does `provider_create_thread` verify the named recipient belongs to the caller's own tenant?
- Does `provider_mark_read`/`staff_mark_read` verify the target notification belongs to the caller (not merely the caller's tenant)?

None of these were verified this slice (out of scope — this is a discovery slice, not an implementation slice) but are flagged as the exact investigation points for 2F-18.

## No product-policy blocker identified
Unlike `compliance.provider_router` (DPDP export-generation rate limiting) or `package_commerce.tenant_router` (purchase entitlement semantics), this module's fix does not appear to require any product decision — it is a straightforward authorization-gap closure following an established pattern.
