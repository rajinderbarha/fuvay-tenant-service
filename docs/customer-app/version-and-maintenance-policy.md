# Customer App — Version and Maintenance Policy

## Version Policy

`src/remote-config/version-policy.ts`. Versions are parsed and compared as
structured semver (`compareVersions`), never as strings — verified by
`1.10.0 > 1.9.9` and `2.0.0 > 1.99.99` tests. Build numbers are compared as
opaque strings against a blocklist (`blockedBuildNumbers`), not numerically
— the schema allows any string, since build-number formats vary by CI
system.

Outcomes (`VersionPolicyOutcome`): `supported-current`,
`supported-update-available`, `supported-update-recommended`,
`grace-period`, `mandatory-update`, `blocked-build`, `unsupported-os`
(reserved — no OS-version field exists in the schema yet, see known-gaps),
`invalid-policy` (malformed version strings anywhere in the policy — fails
closed, never silently treated as "supported").

Precedence inside `evaluateVersionPolicy`: invalid policy → blocked build →
mandatory (policy flag OR below minimum, honoring grace period if
configured and still within the window) → update-recommended/available
(behind latest) → current.

Grace period: `gracePeriodHours` + a caller-supplied
`belowMinimumSinceIso` timestamp. **Known limitation**: this sprint does
not yet persist "when did this device first fall below the minimum
version" — the startup service does not currently pass
`belowMinimumSinceIso` into `evaluateVersionPolicy`, so grace periods are
implemented and tested in `version-policy.ts` but not yet wired end-to-end
from `startup-service.ts`. Tracked in `known-gaps.md`.

## Maintenance Policy

`src/remote-config/maintenance-policy.ts#evaluateMaintenancePolicy` is
timezone-safe by construction — it only ever compares two absolute ISO
timestamps (`startAt`/`estimatedEndAt`, both server-provided) against a
caller-supplied `nowIso`, never deriving a window from the device's local
time zone.

Statuses: `none` (disabled or `type: "none"`), `scheduled` (now <
`startAt`), `active` (within window), `expired` (now ≥ `estimatedEndAt`).
`blocking` is true only for `type: "active-blocking"`; `readOnly` is true
only for `type: "active-read-only"` (the read-only UI treatment itself is
not implemented this sprint — only the policy evaluation, per L5-01 §21's
instruction to "prepare interfaces... but do not fake unsupported business
behavior"). `retryAllowed` passes through the config's own flag.

## Platform / Marketplace-Specific Policy

The schema does not currently carry per-platform or per-marketplace
maintenance/version overrides — a single `versionPolicy`/`maintenance`
object applies to the whole envelope, and the envelope itself is already
marketplace-bound (one config per marketplace context). Splitting policy
further by platform within one marketplace is deferred — no product
requirement was given for it this sprint, and the schema can be extended
without a breaking change later (add `iosOverride`/`androidOverride`
optional fields).
