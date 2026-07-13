# MODULE-L5-00A — `vertical_billing` Disposition (explicit, resolved)

## Investigation (Part 5 requirements)

| Question | Answer | Evidence |
|---|---|---|
| Does any active code call it? | No | `grep -rl "from.*vertical_billing\|import.*vertical_billing" app/ --include="*.py"` returns only the module's own `__init__.py` — no external caller found |
| Does any table belong uniquely to it? | No | No `__tablename__` anywhere in `app/engines/vertical_billing/` (confirmed by `module_inventory_scan.py`: `has_models: false`) |
| Does any migration depend on it? | No | The real `VerticalBillingConfig` table (if it exists in the DB) is owned by `platform_commerce`'s models, not this directory |
| Can it be removed? | **Yes, safely** — no router, no model, no caller | Direct inspection |
| Does it require a compatibility shim? | No | Nothing depends on it |
| Must its false "Proven Level 5" claim be deleted? | **Yes** | `app/engines/vertical_billing/constants.py` docstring, lines 1-15, explicitly reused business language ("proven patterns," "Proven Level 5") describing an architecture that is real — but implemented entirely in `platform_commerce`, not here |

## Disposition

**`DEPRECATE_AND_MIGRATE`** (not `REMOVE_NOW`, out of caution — see rationale below).

Rationale for not choosing immediate `REMOVE_NOW` in this bounded foundation sprint: per Rule 34 ("do not implement broad module functionality in this foundation sprint") and Rule 53 (MODULE-L5-00's own text, carried forward: "do not use this sprint to implement a large module workflow"), deleting a directory — even a confirmed-dead one — is a code change beyond this sprint's declared bounded-tooling-fix scope (Rule 35: "small registry/tooling fixes... do not implement large business functionality"). The safer, equally honest action is to formally register the disposition and correct the false claim in documentation now, and schedule the actual deletion as a tiny, explicit, reviewable diff in `MODULE-L5-00A` follow-up or the Finance/Billing module sprint (`MODULE-L5-09`).

## Required follow-up action (registered, not yet executed)

- Delete `app/engines/vertical_billing/` entirely (or, if a product reason exists to keep the directory as a placeholder for a genuinely future per-vertical billing mode, replace its docstring's false "Proven Level 5" claim with an explicit "NOT IMPLEMENTED — see `platform_commerce`" notice).
- Confirm zero test references to the dead engine path before deletion. `grep -rl "vertical_billing" tests/` finds one match, `tests/test_phase14.py::test_vertical_billing_config_has_versioning_columns` — but this test imports `VerticalBillingConfig` from `app.engines.platform_commerce.billing_models`, not from `app.engines.vertical_billing`; the name reflects the business concept, not the dead directory. This reinforces rather than contradicts the disposition.
- This is tracked as backlog item **BL-002** (`docs/module-l5/34-implementation-backlog.md`) and gap **MODULE-L5-00A-016** below.

## Guard enforcement

`e2e/vertical_billing_guard.js` (this sprint, new) fails closed if any of the following becomes true in the future: `vertical_billing` is claimed Level-5-complete anywhere in `docs/`, it gains a router or unique table without a corresponding registry update, or `platform_commerce`'s ownership of `VerticalBillingConfig` is contradicted by a future code change.
