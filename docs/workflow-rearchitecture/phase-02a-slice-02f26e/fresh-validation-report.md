# Fresh Holdout Validation Report — Slice 2F-26E

## Result: 19/24 all-field agreement. Required 24/24. **Gate fails.**

| Field | Agreement |
|---|---|
| Capability | 21/24 |
| Side effect | 23/24 |
| Persona | 23/24 |
| Tenant direction | 22/24 |
| **All four** | **19/24** |

Against Slice 2F-26D's 4/24 on its own holdout, this is a large improvement —
but "much better" is not the contract. Any disagreement ⇒ zero canonical
edits.

## Freeze ordering

| Event | Time | Hash |
|---|---|---|
| Classifier frozen | 11:09:45 | `be7512782ad70956` |
| Holdout manifest frozen | 11:09:45 | `aeeb3fe510bf9671` |
| Manual verdicts frozen | 11:11:29 | `b02f35736a79eb3d` |
| Classifier first run on holdout | after 11:11:29 | — |

Both hashes are asserted in tests. Zero overlap with the 24 burned routes
(verifier condition N19).

## The five disagreements

### 1. `POST /v1/commerce/warranty/claims` — real classifier defect (3 fields)

```python
tid: uuid.UUID = Query(..., alias="tenant_id")
```

A client-supplied tenant arriving under a **parameter alias**. The parameter
scan looks for a parameter *named* `tenant_id`; this one is named `tid`. The
classifier therefore saw no tenant, fell through to the self-scope rule
(`u.user_id` is used as the claimant), and returned
`NO_TENANT_AUTHORITY_REQUIRED` / `SELF_SERVICE_MUTATION`.

Manual is right: this is `CLIENT_ASSERTED_TARGET_TENANT` /
`TENANT_PROVIDER_MUTATION`.

**Not fixed this slice.** The defect was found *by* the holdout that measures
the classifier; repairing it and re-running the same holdout would be exactly
the circular proof the mission forbids.

### 2. `POST /v1/auth/staff/{user_id}/invite/resend` — real classifier defect

Tool returned `NO_TENANT_AUTHORITY_REQUIRED`, inferring self-scope from
`uuid.UUID(user.user_id)`. But that value is the **actor** argument
(`resend_invite(user_id, actor)`), not the scope — the subject is the
`{user_id}` in the path. Actor identity and scoping identity are different
things and the rule conflates them. Manual abstained
(`REQUIRES_MANUAL_TENANT_ADJUDICATION`) because tenant scoping happens inside
the service and is not traceable from the handler.

Same root cause family as #1: a heuristic reading identity use as scope
evidence.

### 3. `GET /v1/ds/tenants/{tenant_id}/demand/forecast` — **the tool was right, I was wrong**

I recorded `PURE_READ`. The tool said `DATABASE_MUTATION`. Verified in the
service:

```
self.db.add(DemandForecast(tenant_id=tenant_id, forecast_date=today(), ...))
await self.db.flush()
```

A genuine mutating GET — the same family as the deposit lazy-create found in
2F-26C. My manual pass is not infallible either, and this is recorded as a
manual error, not a tool error.

### 4-5. `GET /v1/compliance/consent/users/{user_id}` and `POST /v1/appointments/{appointment_id}/reschedule` — taxonomy granularity (partly mine)

Both disagree on **capability only**; persona and direction agree exactly
(both abstain, with matching reason codes). I wrote `AMBIGUOUS` in the
capability column when what I meant was that the *persona* was undecidable;
the tool correctly reported the capability as `ANY_AUTHENTICATED` and *then*
abstained on persona.

This is a manual-sheet modelling error of the same shape as D-03 — a field
used to carry a judgement it was not defined to carry — though this time it
does not involve a value outside the enum. Counted as disagreement regardless.

## Honest scoring

Of five disagreements: **2 are real classifier defects**, **1 is a manual
error where the tool was correct**, and **2 are capability-column granularity
errors that are substantially mine**. Reporting this as "the classifier failed
5 times" would overstate the tool's fault; reporting it as "only 2 real
defects, therefore pass" would defeat the gate. Both are stated.

## Abstention contract

Manual abstained on 3 routes; the tool abstained on the same 3, with matching
reason codes (`OWNERSHIP_CHECK_IN_SERVICE_NOT_TRACEABLE`). No abstained route
is used to justify any canonical edit. Verifier condition N10 asserts that an
abstained manual verdict is never scored as agreement.

Abstention rate on the fresh holdout is 3/24 — down from a rate that would
have been far higher before repair, and every one has a permitted cause.

## Consequence

Zero canonical edits. Hash `45244cd9540456db` preserved.
**GLOBAL_COVERAGE_RECONCILIATION_BLOCKED.**

The next slice must fix the alias-blind parameter scan and the
actor-versus-scope conflation, then validate against a **third**, newly frozen
holdout. This holdout is now burned.
