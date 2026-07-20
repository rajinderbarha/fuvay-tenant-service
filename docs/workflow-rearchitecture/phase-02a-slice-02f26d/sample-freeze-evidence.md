# Sample Freeze Evidence — Slice 2F-26D

## Ordering (the whole point of the slice)

| # | Event | Timestamp | Hash |
|---|---|---|---|
| 1 | Inputs frozen | 2026-07-19T10:50:11 | canonical `45244cd9540456db`, resolver `b1e61c218e745194`, verifier(26C) `c771b9a201c18774` |
| 2 | Sample selected and frozen | 2026-07-19T10:53:20 | manifest `bc878c81f76e54e6` |
| 3 | Manual adjudications frozen | 2026-07-19T10:55:21 | manual `ad0e23e162b4fb6c` |
| 4 | Classifier run for the first time this slice | after step 3 | — |
| 5 | Comparison produced | after step 4 | — |

Steps 2 and 3 both complete **before** step 4. Both hashes are asserted in
`tests/test_phase2f26d_blinded_validation.py`; if either file were edited
after the fact the test fails, so the ordering claim is falsifiable rather
than asserted.

## Selection method

Selection used **structural** attributes only — HTTP method, path prefix,
and presence of `{tenant_id}` — never any classifier output column. Strata:

| Stratum | Population | Sampled |
|---|---|---|
| 01 platform-admin path targeting a tenant | 18 | 4 |
| 02 tenant-owner mutation | 7 | 3 |
| 06 provider surface | 2 | 2 |
| 11 client-supplied target tenant | 28 | 5 |
| 15 generic prefix (the blind-spot class) | 64 | 8 |
| 20 GET within the mixed population | 4 | 2 |
| **Total** | **123** | **24** |

Within each stratum the pool was sorted deterministically and sampled at an
even stride, so the sample is not just the alphabetical head.

## Blinding — precise scope, and its limits

**What is genuinely blind:** the classifier in question
(`resolve_guards_2f26b.py`) had never been run against these 123 routes.
Its verdicts for the sample did not exist when the manual verdicts were
frozen.

**What is not blind, and is declared as such:**

- `POST /v1/provider/notifications/mark-all-read` was a **control fixture in
  Slice 2F-26B** — its persona answer was already known to me. It is marked
  `CONTROL_FIXTURE_NOT_BLIND` in the manifest. Including it is useful (it
  exercises the guard-alias path) but it cannot count as independent
  evidence for persona.
- Slice 2F-26A ran an **earlier, different and since-discredited** adjudicator
  over this population, and I saw its aggregate counts and a handful of rows.
  That tool's verdicts are not the ones under test here, but the exposure is
  real and is recorded rather than omitted.

Excluding the one declared control route, agreement does not improve: it
agreed on persona and disagreed on tenant direction, exactly like its
un-exposed sibling `POST /v1/provider/notifications/{notification_id}/read`.

## Manual method

Each of the 24 handlers was read directly from mounted-route source — the
decorator, the full signature including every `Depends(...)`, and the body —
and adjudicated on nine fields. No classifier helper was called; the dump
script resolves routes and prints text only.
