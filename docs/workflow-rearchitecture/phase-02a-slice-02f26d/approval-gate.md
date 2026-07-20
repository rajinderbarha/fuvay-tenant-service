# Slice 2F-26D Approval Gate

## Final status

**CLASSIFIER_VALIDATION_FAILED_CANONICAL_UNCHANGED**

The blinded sample ran, and it found defects. Per the mission's explicit
rule — *"If the sample finds a defect: Stop blocked"* — the slice stops here
with zero canonical edits.

## Coverage and hash

`CURRENT_CANONICAL_COVERAGE`: **214 / 257**, 43 unprotected — unchanged.

Canonical hash **before `45244cd9540456db`**, **after `45244cd9540456db`** —
byte-identical, asserted by `test_hash_unchanged`.

The proposed expansion to **214/259 with 45 unprotected** was **NOT applied**.

## The result

| Dimension | Agreement | Required |
|---|---|---|
| Persona | 14/24 (2 DISAGREE, 8 abstained) | 100% |
| Tenant direction | 6/24 | 100% |
| **Combined (every field)** | **4/24 = 16.7%** | **100%** |

## Quality gates

| # | Gate | Status |
|---|---|---|
| 1 | Sample ≥20, stratified, frozen before any verdict | **MET** — 24 routes, 6 strata, hash `bc878c81f76e54e6` |
| 2 | Manual verdicts frozen before classifier run | **MET** — hash `ad0e23e162b4fb6c` |
| 3 | Blinding scope stated honestly incl. prior exposure | **MET** — one control route declared non-blind |
| 4 | Field-by-field comparison | **MET** |
| 5 | 100% agreement | **NOT MET** — 4/24 |
| 6 | Verifier negative fixtures, 16 conditions | **MET** — each proven able to fail (`--selftest`) |
| 7 | Verifier exits non-zero | **MET** — real exit code 1, six conditions |
| 8 | Two proposed routes independently reconfirmed | **MET** — both mounted, both `require_permission(P.TENANT_UPDATE)` |
| 9 | Nine other hidden-side-effect dispositions | **NOT DONE** — see disclosures |
| 10 | Strict edit gate enforced | **MET** — gate failed, zero edits |
| 11 | Classifier not tuned to pass its own sample | **MET** — resolver hash `b1e61c218e745194` unchanged, asserted |
| 12 | Provisional queue rebuilt | **N/A** — no expansion occurred |
| 13 | Hashes reported before and after | **MET** |
| 14 | Behavioural invariants pass | **MET** — 6 invariants |
| 15 | No behaviour/role/permission/migration change | **MET** — zero `app/` files modified |

## What this slice actually established

**The foundation declared trustworthy in 2F-26B/26C is not trustworthy.** It
had only ever been checked against two hand-picked control routes. Measured
against 24 routes it had not seen, it agrees on every field 4 times out of 24.

**One defect is the specific error the previous mission warned against.**
2F-26C was told not to treat `{super_admin}` as the complete admitted set for
runtime-extensible permissions. It proved the correct semantics in tests and
in the verifier — and left the classifier using the old assumption. Two
sampled routes are mis-classified as platform-admin as a direct result.

**A dimension introduced in 2F-26B was never tested by the fixture meant to
validate it.** The `mark-all-read` control asserted persona only; tenant
direction is wrong on that very route.

This is the ordering rule earning its cost. Had the two proposed rows been
applied on 2F-26C's "strong evidence", they would have been merged on a
foundation now measured at 16.7%.

## Honest disclosures

- **Four of the eighteen tenant-direction disagreements are my error**, not
  the classifier's — my manual sheet used `NO_TENANT_SCOPE`, a label outside
  the tool's vocabulary. Condition C13 fails on this; the taxonomy must be
  reconciled before the next sample.
- **Eight `REQUIRES_MANUAL_ADJUDICATION` verdicts are correct fail-safe
  behaviour**, not wrong answers — but they are not agreement either, and a
  classifier abstaining on a third of routes cannot carry a denominator.
- **The nine remaining hidden-side-effect dispositions were not
  reconfirmed.** Once the gate failed on Workstream 3 the expansion was
  unreachable, and reconfirming inputs to a decision that cannot be taken
  would be work performed for the appearance of completeness.
- **Not all 32 documents are produced.** Files describing a passing sample,
  an applied expansion or a rebuilt queue would describe work that did not
  happen. Nine real artifacts were produced.
- **This sample is now burned.** It cannot validate a repaired classifier.
- **The observations in `authorization-observations-not-remediated.md` are
  from static reading only** — none was executed against a live tenant pair.

## Preserved

Zero application files modified; zero authorization behaviour changed;
canonical byte-identical. Closures asserted intact by behavioural invariants
— field_ops job-close, Package Commerce, customer_reviews, legacy review
(incl. 410), compliance. Canonical roles only; no role, permission or
migration added; no pipeline merged; `PartsRequest` ServiceJob-only;
`readonly@demo-ac-services.local` untouched; Migration 144 unapplied;
Slice-2D canaries untouched; `quote_checklist` untouched.

## Stop condition

Stops at the Slice 2F-26D approval gate. No module selected, no authorization
implemented, no canonical change.

**The next slice must:** reconcile the tenant-direction taxonomy (D-03), wire
runtime-extensible permission semantics into the classifier's persona
assignment (D-01), make `tenant_authority()` consistent for guards it already
resolves elsewhere (D-02), reduce abstention (D-04) — and then validate
against a **newly frozen holdout sample**, not this one.
