# Canonical CSV Structure Decision

## The two canonical CSVs
1. `docs/workflow-rearchitecture/phase-02a-slice-02f/tenant-mutation-endpoint-inventory.csv` — the row-level inventory that `test_canonical_totals` counts against. This is the source of the **X/Y headline figure**.
2. `docs/workflow-rearchitecture/phase-02a-slice-02f/mutation-enforcement-matrix.csv` — a per-MODULE summary (one row per router file), used for at-a-glance module status, not for computing the canonical X/Y.

## Design chosen: **A — tenant/provider mutations only**, for CSV #1
`tenant-mutation-endpoint-inventory.csv` is, and always has been (since Slice 2F-1), a tenant-facing mutation inventory — every prior slice's rows in this file represent tenant/provider-side mutations exclusively. Introducing an `include_in_tenant_denominator` column (Design B) would be a structural change to a file with 200+ pre-existing rows, none of which carry that column, for a benefit (self-documenting filterability) that a physical-removal approach already achieves more simply: if a row doesn't belong in the tenant-facing count, it doesn't belong in the file.

**Consequence of Design A**: `create_booking`, `cancel_booking`, `request_reschedule` (customer self-service) and `void_booking` (platform-internal) were **physically removed** from `tenant-mutation-endpoint-inventory.csv` this slice (as `booking_preflight` was in 2F-15B). They are NOT tracked in any separate customer/platform CSV in this initiative — their protection status is recorded in this slice's own `final-booking-route-persona-table.csv` and `booking-coverage-row-diff.csv` instead, and re-verified live via the runtime tool's `persona_breakdown` on every run (not a static, driftable file).

## Why CSV #2 (`mutation-enforcement-matrix.csv`) intentionally differs
This file's established convention (unchanged since Slice 2F-1) is "total MOUNTED mutation-method routes per module," not "tenant-facing mutations per module" — e.g. its `app.engines.booking.router` row reports `11` total (all mounted routes) with `10` "protected" (10 genuine mutations, all correctly guarded for their respective persona; `booking_preflight` is the 1 non-mutation). This is a deliberately different denominator than CSV #1's tenant-only convention, and has been for every module in this file across the whole initiative (e.g. `app.engines.field_ops.staff_router`'s row counts all 6 mounted routes, none of which are customer-facing, so the two conventions happen to coincide there but diverge for `booking.router`, which is the first module in this initiative with a real customer-self-service persona).

## Applying the same rule consistently
Both CSVs apply their OWN internally consistent rule: CSV #1 never contains a customer/platform/false-positive row (enforced this slice by physical removal); CSV #2 always reports the full mounted-route count per module, with its own row-level clarifying text explaining any non-tenant-facing subset (as this slice's updated `mutation-enforcement-matrix.csv` row for `booking.router` now does explicitly). Neither convention changed for any OTHER module in either file this slice — this is scoped entirely to `booking.router`'s 4 non-tenant rows.

## Automated recount is the runtime tool, not a CSV column
Rather than adding an `include_in_tenant_denominator` boolean column to a 200+ row CSV (Design B), the mission's "automated recount must filter" requirement is satisfied by the runtime tool's `persona_breakdown`/`tenant_denominator_count` fields (see `runtime-documentation-drift-check.md`), which is regenerated live on every invocation and cannot silently drift from the code the way a static CSV column could.
