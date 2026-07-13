# MODULE-L5-00A — Expanded Gap Register

Builds on MODULE-L5-00's 10-item backlog. New/refined items this sprint:

| Gap ID | Requirement | Module | Application | Role | Layer | Type | Severity | Evidence | Future sprint |
|---|---|---|---|---|---|---|---|---|---|
| MODULE-L5-00A-001 | All 68 engines must map to a canonical module | (cross-cutting) | N/A | N/A | Requirements | N/A | N/A | `canonical_module_reconciler.py` first run found `promo` unmapped; fixed same session | Closed this sprint |
| MODULE-L5-00A-015 | REQ-009 (technician quote submission) | `job_lifecycle` | `staff_app_mobile` | `technician` | Frontend | `MISSING_FRONTEND` (`BACKEND_ONLY_UI_REQUIRED`) | HIGH | Direct inspection: `quote_checklist` engine has real endpoints; `mobile/staff-app`'s 8 screens confirmed to have no Quote/Inspection screen | `MODULE-L5-08` |
| MODULE-L5-00A-016 | REQ-012 (Security Policy ownership) | `compliance_security_ops` | `super_admin` | `admin_security` | Permissions | `PRODUCT_DECISION_REQUIRED` | MEDIUM | Carried from FINAL-L5-05AL/AM, still unresolved | Blocked on product decision |
| GAP-EXP-001 | REQ-007 (cancellation/reschedule pipeline connection) | `booking_matching_scheduling` | `customer_app_web`, `customer_app_mobile` | `customer` | Business logic / data flow | `DISCONNECTED_PIPELINE` | **CRITICAL if confirmed** | Carried forward from mission brief's own assertion; NOT independently re-traced this sprint | `MODULE-L5-07` |
| GAP-EXP-003 | REQ-002 (Security Deposit 5-role runtime proof) | `packages_credits_deposits` | `super_admin`, `tenant_portal` | `admin_finance`, `tenant_owner` | Runtime test | `MISSING_TEST` | MEDIUM | FINAL-L5-05AL source-verified only | `MODULE-L5-06` |
| GAP-EXP-005 | REQ-006 (booking->matching->assignment cross-app E2E) | `booking_matching_scheduling` | `customer_app_web/mobile`, `tenant_portal` | `customer`, `tenant_owner`, `staff`, `technician` | E2E test | `MISSING_E2E` | HIGH | No cross-application E2E test found referencing this full chain | `MODULE-L5-07` |
| GAP-EXP-006 | REQ-010 (job completion -> commission trigger) | `finance_ledger_commission` | `staff_app_mobile`, `tenant_portal`, `super_admin` | `technician`, `tenant_owner`, `admin_finance` | Business logic / data flow | `DISCONNECTED_PIPELINE` (unconfirmed) | **CRITICAL if confirmed** | Carried forward from mission brief's own known-pattern list; NOT independently re-traced this sprint | `MODULE-L5-09` |
| GAP-EXP-009 | REQ-004 (customer-app serviceability check runtime) | `geography_serviceability` | `customer_app_web`, `customer_app_mobile` | `customer`, `guest` | Runtime test | `MISSING_TEST` | MEDIUM | Backend confirmed real (29 endpoints); frontend runtime call not independently verified this program | `MODULE-L5-03` |
| GAP-EXP-010 | 21 of 68 engines flagged `PARTIAL_NO_UI_NO_TEST_MATCH` by MODULE-L5-00's scanner require manual per-engine confirmation (real gap vs. heuristic false negative) | Various (see `03-module-registry.json`) | Various | Various | Multiple | Mixed, pending confirmation | MEDIUM | MODULE-L5-00 finding, not yet resolved | Per-module `MODULE-[ID]-L1` sprints |
| GAP-EXP-011 | Pre-05 "release candidate" declaration set (12 files) vs. 13 subsequent FINAL-L5-05 sprints' real defect discoveries — never formally reconciled | (cross-cutting) | N/A | N/A | Documentation | Process gap | MEDIUM | MODULE-L5-00 finding, carried forward, not resolved this sprint either (bounded scope) | `MODULE-L5-00B` (recommended, not yet scheduled) |
| GAP-EXP-012 | Full 40-layer-cell matrix (Part 16) not built per-module this sprint — only module boundary/engine-list level (Part 4) delivered | All 17 canonical modules | All | All | All 40 layers | `MISSING_TEST` / documentation depth | HIGH | This sprint's own bounded scope decision, honestly disclosed | Each module's future `MODULE-[ID]-L1` sprint |

`vertical_billing`'s false "Proven Level 5" claim (tracked as MODULE-L5-00-002 in MODULE-L5-00) is now **closed** — the docstring was corrected this sprint (see `00a-vertical-billing-disposition.md`); the directory's scheduled deletion remains open as backlog item **BL-002**.

## Summary

- Gaps carried forward from MODULE-L5-00, still open: 8 (BL-001, BL-002 [docstring fixed, deletion still open], BL-003 through BL-010)
- New gaps this sprint: 9 (MODULE-L5-00A-001 [closed same session], 015, 016, GAP-EXP-001, 003, 005, 006, 009, 010, 011, 012)
- Closed this sprint: 2 (MODULE-L5-00A-001 promo-mapping fix; the false Level-5 claim removal)
- Critical (if confirmed): 2 (GAP-EXP-001, GAP-EXP-006 — both explicitly flagged as carried-forward assertions requiring a future direct code-trace, not independently re-verified this bounded sprint)
- High: 3 (MODULE-L5-00A-015, GAP-EXP-005, GAP-EXP-012)
- Medium: 5 (MODULE-L5-00A-016, GAP-EXP-003, 009, 010, 011)
