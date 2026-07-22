# Known Limitations — Slice 2E

1. **`technician` and `tenant_owner` accounts never get `StaffPermission` overrides loaded into their JWT** — `_build_token_pair`'s `if user.role == "staff":` gate excludes them. Not fixed this slice (out of scope — the manager/read-only personas both target `staff`-role accounts).
2. **Read-only mutation-guard coverage remains at 1 of 16 tenant router files** — this slice precisely measured the gap (previously an estimate) but did not close it. This is the single largest remaining blocker in the whole tenant-access-model closure effort.
3. **`readonly@demo-ac-services.local` remains unremediated** — correctly, per the brief's own stop condition.
4. **Manager persona lacks several needed permission constants** (team-wide job/quote/customer visibility, finance view/modify, business-settings modify) — the mechanism works, but a fully-featured manager persona needs new `P.*` constants and corresponding service-layer filter changes not built this slice.
5. **Permission changes (via `update_permissions`) do not trigger automatic session revocation** — a newly-undocumented-until-now finding (Slice 2C/2D covered role changes; this slice confirms the same stale-JWT characteristic applies equally to permission changes specifically).
6. **Service-layer bypass audit was not comprehensive** — spot-checked 3 representative methods; a full caller-graph audit across ~140 engine service classes was not attempted.
7. **`tenant-mutation-route-inventory.csv` and `mutation-enforcement-matrix.csv` are router-file-level, not exhaustive per-endpoint** — several brief-listed domains (service areas, availability, customers, media, settings) were not confidently mapped to a specific router file and are marked UNVERIFIED rather than guessed.
8. **A full-repository `pytest tests/` run was not completed** — time-boxed at ~5% progress with zero failures; the 287-test targeted regression suite (covering the areas most likely affected by this slice's one core change) is the primary evidence of no regression.
9. **Pre-existing duplicate-operation-ID warnings** in `service_setup/templates_router.py` remain, unrelated, not fixed (same as every prior slice).
