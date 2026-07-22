# Current Canonical Coverage (post Slice 2F-36)

- Canonical denominator: **297**
- Protected: **294**
- Unprotected: **3** (Set C, deliberately untouched, assigned to future slices)
- Pending held candidates: **17**
- Canonical CSV hash: `72932524e0aa17b3`
- Mutation-enforcement matrix hash: `7cd530722272193e`

This matches exactly the mission's stated expected position for full
Set A/B closure: "Canonical unprotected: 3, Pending held: 17."

This coverage figure applies to the tenant-mutation canonical CSV only
(Design A: tenant-provider-persona mutations). It does not represent
application-wide authorization coverage — customer-self-service,
platform-admin, and platform-internal mutations are tracked separately
and are out of this denominator by design (see `booking.router`'s
CUSTOMER_SELF_SERVICE_MUTATION convention, established Slice 2F-15C).
