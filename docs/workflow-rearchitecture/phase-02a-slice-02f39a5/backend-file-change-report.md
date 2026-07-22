# Backend File Change Report — Slice 2F-39A5

## Application files changed (4)

- `app/engines/platform_commerce/billing_endpoint.py` (`route_operation`
  guard change)
- `app/engines/appointment/service.py` (`hold_slot` tenant check)
- `app/engines/analytics/router.py` (`ingest_event` guard change)
- `app/engines/notification/router.py` (`send_notification`, `retry`
  guard changes)

## Test files changed/added (4)

- `tests/test_phase2f39a5_final_decisions.py` (new, 7 tests)
- `tests/test_phase2f26f_alias_actor_scope.py` (classifier exemption update)
- `tests/test_phase2f26g_family_precedence_ast_writes.py` (classifier
  exemption update)
- `tests/test_phase2f26h_tokenized_action.py` (classifier exemption update)

## New scripts (1)

- `scripts/workflow_rearchitecture/cert_guard_2f39a5.py`

No migrations, no frontend, no mobile, no demo-role/seed scripts.
