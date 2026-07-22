# Set C Non-Regression Report - Slice 2F-29

No Set C route was modified.

| Set C route | Status | Evidence |
|---|---|---|
| `/v1/security/api-keys/{key_id}/rotate` | untouched | separate subsystem; `tenant_api_keys` table asserted |
| `/v1/security/api-keys/{key_id}/revoke` | untouched | same |
| `/v1/security/sessions/{session_id}/revoke` | untouched | different router/service |
| `/v1/auth/mfa/setup` | untouched, still protected | not in Set A; guard unchanged |
| `/v1/auth/logout` | untouched | not in Set A |
| `/v1/auth/sessions/{session_id}` | untouched | not in Set A |
| `/v1/auth/staff/{user_id}/schedule` | untouched (held) | not canonical |
| `/v1/auth/staff/{user_id}/invite/resend` | untouched (held) | asserted `access_scope_gated=False`, i.e. not modified |

The Set C hash is unchanged (`c77889cac83f07be`). No test protecting a Set C
route was weakened.
