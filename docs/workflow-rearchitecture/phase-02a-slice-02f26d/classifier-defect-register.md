# Classifier Defect Register — Slice 2F-26D

The blinded 24-route sample reached **4/24 = 16.7%** combined-field agreement
against a required 100%. Three distinct causes, separated because they have
different owners and different remedies.

---

## D-01 — Runtime-extensible permissions collapsed to `{super_admin}`

**Severity: high — this is the error 2F-26C's mission explicitly named.**

Affected: `POST /v1/tenants/{tenant_id}/plan/upgrade`,
`POST /v1/tenants/{tenant_id}/terminate/confirm`.

Both are guarded by `require_tenant_mutation_permission(P.TENANT_PLAN_MANAGE)`
and `(P.TENANT_TERMINATE)`. Neither permission appears in `ROLE_PERMISSIONS`,
so static resolution yields `{super_admin}` and the classifier concludes
`PLATFORM_ADMIN_MUTATION`. Directly measured:

```
tenant:plan:manage  in ROLE_PERMISSIONS: False
   super_admin: True | tenant_owner: False | tenant_owner+grant: True
tenant:terminate    in ROLE_PERMISSIONS: False
   super_admin: True | tenant_owner: False | tenant_owner+grant: True
```

A `tenant_owner` holding a StaffPermission grant **is admitted**. The
handlers corroborate this: each calls `_assert_own_tenant_or_super_admin`,
a check that is dead code if only super-admins can ever arrive.

**Why this survived 2F-26C.** That slice proved runtime extensibility in
*tests* and wrote it into the *verifier*, but never wired it into the
classifier's persona assignment. The tests passed while the classifier
using the old assumption went unmeasured. A property proven in a test is not
a property held by the tool.

Consequence: two genuine tenant mutations would have been excluded from the
denominator as platform-admin routes.

---

## D-02 — Tenant direction unresolved on 14 of 24 routes

`tenant_authority()` returned `UNKNOWN_TENANT_ROLE` for 14 routes whose
direction is determinable by reading the guard, including cases the tool
resolves correctly elsewhere — `require_tenant_mutation_permission` yields
`PRINCIPAL_TENANT` on `/v1/tenants/...` but `UNKNOWN` on
`/v1/tenant/service-areas/{area_id}/services` and on the checklist-template
route. The inconsistency, not the conservatism, is the defect.

It also returned `UNKNOWN` for `_provider_guard` on both provider
notification routes — including the 2F-26B control fixture. **2F-26B's
control asserted persona only.** The tenant-direction dimension it introduced
was never actually tested by the fixture that was supposed to validate it.

---

## D-03 — Vocabulary mismatch (my error, not the tool's)

4 disagreements are mine. My manual sheet used `NO_TENANT_SCOPE`, which is
not in the tool's emitted vocabulary
(`PRINCIPAL_TENANT | PLATFORM_ADMIN_TARGET_TENANT | CLIENT_ASSERTED_TENANT |
UNKNOWN_TENANT_ROLE`). A label the tool cannot produce can never agree.

Counted as non-agreement anyway — the gate is not graded on a curve — but
attributing it to the classifier would overstate the classifier's fault.
Condition **C13** now fails on exactly this, so the next slice must reconcile
the taxonomy before sampling.

---

## D-04 — `REQUIRES_MANUAL_ADJUDICATION` on 8 routes

Not a defect: it is the correct fail-safe outcome, and 2F-26B was right to
prefer it over a guess. But it is also **not agreement**, and a classifier
that abstains on a third of the population cannot carry a denominator. Gate
condition **C11** records this separately from the two real disagreements so
the two are never conflated.

---

## Deliberately not fixed

The mission forbids tuning the classifier and re-running the same sample as
independent proof. No line of `resolve_guards_2f26b.py` was modified this
slice — asserted by `test_classifier_source_was_not_tuned_this_slice`
(hash `b1e61c218e745194`). Repair requires a later slice with a **newly
frozen holdout sample**; this sample is now burned for validation purposes.
