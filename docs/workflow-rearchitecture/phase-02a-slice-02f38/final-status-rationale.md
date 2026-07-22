# Final Status Rationale

Considered tokens, in order of the mission's own definitions:

- `APPLICATION_WIDE_MUTATION_AUTHORIZATION_CERTIFIED` — **rejected**: role
  data, migration environment, seed-script guard, and route-census
  completeness all independently fail its required conditions.
- `..._CERTIFIED_WITH_KNOWN_DOMAIN_LIMITATIONS` — **rejected**: this token
  requires "all mutation-authorization requirements pass" with only
  *non-authorization* limitations remaining (N01/payments/read-path/product
  policy). Here, mutation-authorization itself has open items (seed-script
  role guard, incomplete route census) — not merely domain limitations
  layered on top of a clean authorization result.
- `MIGRATION_AND_ROLE_DATA_READINESS_BLOCKED` — **selected**. Matches its
  definition exactly: "route authorization is ready but... one or both
  demo accounts remain MANUAL_ROLE_CONFIRMATION_REQUIRED... or Migration
  144 cannot be safely executed." Both conditions are true. The canonical
  313/313 route-authorization result (the thing this token presupposes is
  "ready") is itself solidly proven; what's blocked is the *readiness of
  role data and the migration*, exactly this token's scope.
- `POSTGRESQL_MIGRATION_ENVIRONMENT_UNAVAILABLE` — **not selected as the
  primary token**: this token's definition requires "role mapping is
  ready but no safe PostgreSQL environment exists" — role mapping is
  *not* ready (both accounts unresolved), so the role-data blocker
  dominates. PostgreSQL unavailability is documented as a compounding,
  independent blocker within the `MIGRATION_AND_ROLE_DATA_READINESS_BLOCKED`
  report rather than as a separate top-level status.
- `AUTHORIZATION_CERTIFICATION_BLOCKED` — considered given the seed-script
  and route-census findings, since both are, strictly, authorization
  gaps. Not selected as the single top-level token because the *canonical*
  mutation-authorization result (this program's primary deliverable) is
  not itself broken — no canonical route lost protection, no cross-tenant
  bypass was found to succeed. The seed-script and route-census gaps are
  real and are called out prominently in `final-certification-report.md`,
  but characterizing the *entire* slice by this token would understate
  the solid 313/313 result and overstate what's actually broken.
- `FULL_REGRESSION_BLOCKED` — considered given 45 full-backend failures.
  Not selected as the top token because all 45 were classified (not
  hidden) and none blocks Phase-2F's own regression (2445/2445 clean,
  twice) — the role-data/migration blockers are the more precise,
  actionable characterization of what actually prevents certification.
- `FROZEN_SCOPE_MISMATCH` — **not applicable**: the baseline (`01e6ee4`)
  is real, committed, and reproducible; no mismatch with the frozen
  contract was found this slice.
- `CONCURRENT_WORKTREE_INTERFERENCE` — **not applicable**: the
  certification guard never fired; the dedicated worktree remained
  isolated throughout.
- `INCOMPLETE` — considered, since several workstreams (full per-route
  census, full-backend regression twice, a dedicated `verify_2f38.py`)
  were not completed to their full mission-specified depth. Not selected
  as the top token because the reason certification cannot proceed is not
  "this slice ran out of time to investigate" in the abstract — it is two
  specific, independently sufficient, well-evidenced blockers
  (`MIGRATION_AND_ROLE_DATA_READINESS_BLOCKED`'s own definition) that
  would still block certification even with unlimited further
  investigation of the *other* dimensions. The incompleteness is recorded
  honestly (`known-limitations.md`, `deferred-items.md`) but does not
  change which token is the accurate top-level characterization.

## Conclusion

**`MIGRATION_AND_ROLE_DATA_READINESS_BLOCKED`**, with `known-limitations.md`
and `final-certification-report.md` making clear that even resolving the
role-data and migration blockers would not by itself yield an unqualified
application-wide certification, given the seed-script and route-census
findings.
