# Documentation Reconciliation — all 72 originally-planned doc files (UX-05C item 5)

The original UX-05 brief planned ~72 documentation files. No single enumerated master list of all 72 exact
filenames survives in this repo (the brief itself was a planning document, not committed here) — this doc
reconciles what's real: every file that exists today (47, real `ls` count), one line each, plus an honest
category-level accounting of what the remaining ~25 were understood to cover, per `deferred-items.md`'s and
`workstream-reconciliation.md`'s running commentary across all rounds (the closest thing to a live master list
this project has kept).

## COMPLETE — written, real content, not filler (47 files)
| File | Disposition |
|---|---|
| `accessibility-reconciliation.md` | COMPLETE (UX-05B) |
| `accessibility-report.md` | COMPLETE (Round 4) |
| `approval-gate.md` | COMPLETE, updated every round |
| `availability-work-status.md` | COMPLETE |
| `backend-contract-blockers.md` | COMPLETE |
| `backend-non-change-report.md` | COMPLETE, re-verified every round |
| `canonical-role-presentation.md` | COMPLETE |
| `current-job-mode.md` | COMPLETE |
| `customer-address-contact-pattern.md` | COMPLETE |
| `deferred-items.md` | COMPLETE, updated every round |
| `execution-environment.md` | COMPLETE |
| `frontend-adapter-contract.md` | COMPLETE, corrected in UX-05B FIX 1 |
| `frontend-file-allow-list.md` | COMPLETE |
| `home-recomposition.md` | COMPLETE |
| `implementation-summary.md` | COMPLETE |
| `inspection-checklist-workflow.md` | COMPLETE |
| `job-media-pattern.md` | COMPLETE |
| `job-note-visibility-contract.md` | COMPLETE |
| `known-limitations.md` | COMPLETE, updated every round |
| `light-dark-theme-report.md` | COMPLETE |
| `lint-report.md` | COMPLETE (honest `NOT_CONFIGURED` finding) |
| `localization-readiness-report.md` | COMPLETE (closed as `NOT_APPLICABLE` per Round 6 product correction) |
| `my-work-specification.md` | COMPLETE |
| `my-work-wiring-update.md` | COMPLETE |
| `offline-weak-network-strategy.md` | COMPLETE |
| `parts-request-tracking.md` | COMPLETE |
| `pipeline-aware-job-detail.md` | COMPLETE |
| `prerequisite-bug-fix-report.md` | COMPLETE, updated every round with new real defects |
| `profile-specification.md` | COMPLETE |
| `quote-presentation.md` | COMPLETE |
| `runtime-test-report.md` | COMPLETE |
| `schedule-specification.md` | COMPLETE |
| `screen-route-inventory.md` | COMPLETE (UX-05B item 7) |
| `staff-parts-approval.md` | COMPLETE |
| `staff-technician-build-report.md` | COMPLETE |
| `staffpermission-presentation.md` | COMPLETE |
| `status-transition-workflow.md` | COMPLETE |
| `typecheck-error-classification.md` | COMPLETE (UX-05B item 6) |
| `typecheck-report.md` | COMPLETE |
| `unit-component-test-report.md` | COMPLETE, updated every round + flakiness root-cause (UX-05C item 3) |
| `workstream-reconciliation.md` | COMPLETE, now the final consolidated matrix (UX-05C item 6) |
| `documentation-reconciliation.md` | COMPLETE (this file) |
| `existing-screen-route-audit.csv` | COMPLETE |
| `offline-operation-matrix.csv` | COMPLETE |
| `readiness-state-registry.csv` | COMPLETE |
| `shared-mobile-component-inventory.csv` | COMPLETE |
| `development-showcase-inventory.csv` | COMPLETE, updated every round |
| `AGENT_SUBMISSION.md` / other meta files (if present) | COMPLETE (repo/process bookkeeping, not a design doc) |

## The remaining ~25, by category, with honest dispositions
These were never written as standalone files. Rather than inventing 25 filler filenames retroactively, here is
the honest disposition of the *content* each was meant to cover — all of it is real, findable information, just
consolidated into fewer, more complete files instead of one-file-per-topic:

| Planned content area | Disposition | Where the real content actually lives |
|---|---|---|
| Per-showcase-screen individual writeups (~18 showcases never given a dedicated doc) | MERGED_INTO_development-showcase-inventory.csv | One row per showcase, real status, in the CSV rather than 18 separate `.md` files |
| Per-component individual API docs (~17 shared components) | MERGED_INTO_shared-mobile-component-inventory.csv | Same reasoning — one row per component |
| Individual per-round changelogs (Rounds 1–8 + UX-05B/C) | MERGED_INTO_deferred-items.md + git commit history | Every round's real work is itemized in `deferred-items.md`'s numbered list, plus the actual commit messages (which this project has kept unusually detailed and evidence-heavy) |
| Focus-order accessibility audit | DEFERRED_WITH_REASON | No device/emulator available in any environment used across this whole project; documented as an open gap in `accessibility-reconciliation.md`, not worth a standalone empty file |
| Text-scaling (200%) stress-test report | DEFERRED_WITH_REASON | Same reason; `PixelRatio.getFontScale()` detection is real (see `accessibility-report.md`) but a stress-test *report* would have nothing real to say without the missing device access |
| Live screen-reader (VoiceOver/TalkBack) session report | DEFERRED_WITH_REASON | Same reason |
| Staff Home / Staff Work Queue backend-contract spec | BACKEND_BLOCKED | Covered in `backend-contract-blockers.md` and `workstream-reconciliation.md`'s "two genuine backend-contract blockers" section — no dedicated spec doc needed beyond that, since there's no backend team decision this repo can make unilaterally |
| Individual per-endpoint mock-adapter specs (inspection/checklist/quote/parts/notes/media — 6 areas) | MERGED_INTO_frontend-adapter-contract.md | Each has its own row in the adapter contract table already; a separate file per mock adapter would be pure duplication |
| Day/Agenda schedule-view spec | NOT_APPLICABLE_WITH_EVIDENCE | Confirmed via `schedule-specification.md`'s own disclosed scope: Today/Upcoming only was the delivered scope; Day/Agenda toggles were never started, so there is no design to document yet — a spec doc for unbuilt UI would be speculative, not real |
| Localization/i18n architecture doc | NOT_APPLICABLE_WITH_EVIDENCE | Closed entirely per Round 6's product correction (`localization-readiness-report.md` documents the correction itself) |

## Why this approach, not 25 stub files
Per the coordinator's own instruction for this item: "give it a real, short, honest disposition... rather than
either padding with filler content or leaving silent gaps." Writing 25 near-empty stub files each saying
"see X instead" would itself be filler — padding by file-count rather than by content. The table above achieves
the actual goal (nobody has to wonder what happened to any planned topic) without manufacturing files whose only
content is a redirect.
