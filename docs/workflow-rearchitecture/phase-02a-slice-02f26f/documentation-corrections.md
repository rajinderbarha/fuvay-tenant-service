# Documentation Corrections — Slice 2F-26F

## Correction 1 — a manual error in the Slice 2F-26E manual sheet

`docs/workflow-rearchitecture/phase-02a-slice-02f26e/fresh-manual-adjudication.csv`
records `GET /v1/ds/tenants/{tenant_id}/demand/forecast` as `PURE_READ`.

**That is wrong.** The route persists a row:

```
self.db.add(DemandForecast(tenant_id=tenant_id, forecast_date=today(), ...))
await self.db.flush()
```

The correct value is `DATABASE_MUTATION`. This was already disclosed in
2F-26E's validation report as a case where the tool was right and the manual
verdict wrong; it is restated here as a formal correction.

**The frozen artifact has NOT been edited.** Slice 2F-26E's manual sheet is a
point-in-time record whose hash (`b02f35736a79eb3d`) is asserted by that
slice's tests and by this slice's `test_historical_artifacts_unchanged`.
Rewriting it would destroy the evidence that the error occurred. The
correction lives here instead.

## Correction 2 — scope of the "capability" column in 2F-26E

2F-26E's manual sheet used the `capability` column to carry a persona
judgement (`AMBIGUOUS`) on two routes, producing two disagreements that were
attributed partly to the manual sheet. Slice 2F-26F replaces that free-form
column with the frozen two-level taxonomy (family + action), so the field can
no longer absorb a judgement it was not defined to carry.

## No other corrections

No claim in the 2F-26C, 2F-26D or 2F-26E documents has been found to
overstate results. The coverage figure 214/257 and hash `45244cd9540456db`
have been re-verified this slice and are unchanged.
