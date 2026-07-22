# Targeted Test Report

- `test_phase2f39a_canonical_additions.py` (4 tests, new): guard-source
  verification for all 3 api-key routes; tenant-scoped-query proof for
  `revoke_api_key`/`update_api_key` (foreign-tenant lookup → not found,
  never mutated); server-derived-tenant proof for `create_api_key`
  (persisted `tenant_id` matches the server-supplied value, not any
  client input — there is no client-supplied tenant_id path in this
  endpoint at all, which is itself the desired property).
- `test_sprint27_notifications.py` (44 tests, 2 fixed): cross-customer
  and cross-tenant chat-thread access denial, both proven via
  `pytest.raises`.

No skips, no retries, no broad timeouts were added to make any test pass.
