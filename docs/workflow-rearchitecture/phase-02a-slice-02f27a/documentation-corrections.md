# Documentation Corrections - Slice 2F-27A

## Correction 1 - "57" vs 59 held candidates

The mission stated hold "the other 57". The honest count is **59**. The two
authorized routes (DELETE /v1/webhooks/endpoints/{endpoint_id}, DELETE
/v1/geo/zones/{zone_id}) were surfaced separately in Slice 2F-26C and were
NEVER among the 59 mixed-persona add-candidates produced by the 2F-27
dual-review over the 123-route population. Therefore 59 - 0 = 59 remain held,
not 57. The hold registry contains 59 rows.

## Correction 2 - "both canonical CSVs"

The repository contains ONE canonical tenant-mutation inventory CSV
(tenant-mutation-endpoint-inventory.csv) plus the module-level
mutation-enforcement-matrix.csv. There is no second per-route canonical CSV.
The two-route addition was applied to the one inventory CSV; two module rows
were added to the matrix.

## Forward annotation on Slice 2F-27 (not rewriting its decision)

- The Slice 2F-27 bulk 59-route proposal remains NON-AUTHORITATIVE.
- Two routes were later explicitly authorized by the user.
- The two-route update was applied only in Slice 2F-27A.
- The other 59 remain pending.
- Slice 2F-27 did not have two genuinely independent human reviewers; it ran
  two automated methodologies operated by one agent (already disclosed in
  2F-27 reviewer-independence-evidence.md).

## Artifact-completeness wording

All 42 Slice 2F-27 required artifact paths exist; blocked-state artifacts may
contain limitation reports rather than completed reconciliation outputs.
