# Secret Handling Report - Slice 2F-29

- **API keys**: raw key generated in `generate_api_key`, returned once by
  `create_api_key` with an explicit warning, persisted only as `hashed_key`.
  Update/revoke responses contain no key material. Audit payloads carry name
  and scopes, never the secret.
- **Passwords**: only hashes are stored (`hash_password`); no password appears
  in a response or audit payload.
- **MFA**: setup secret is issued by the (out-of-scope, already protected)
  setup route; `confirm`/`disable` return no secret material.
- **Impersonation**: the Redis record stores `impersonator:target:reason`
  (truncated), not token material.

No secret, recovery token or MFA seed is logged by any Set A path.
