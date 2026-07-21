# Targeted Test Report

- `test_phase2f39a2_security_apikey_fix.py` (4 tests, new): proves the
  `create_api_key` fix — correct guard used, no client tenant_id trusted,
  missing tenant context rejected before the request body is even
  parsed, and a spoofed body tenant_id is ignored in favor of the
  caller's real tenant.
- `test_phase2f26h_tokenized_action.py` (34 tests, 1 fixed): the
  classifier-corpus exemption for `create_api_key`'s reclassified
  tenant_direction.

No skips, retries, or broad timeouts were added.
