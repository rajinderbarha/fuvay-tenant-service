# Secret/Token Redaction Report (WS8)

## API keys (SecurityService)

- `create_api_key` returns the raw secret ONCE (pre-existing, unchanged
  by this slice — confirmed by reading `create_api_key`, which is not one
  of the 2 routes this slice touched).
- `rotate_api_key`/`revoke_api_key` (both closed this slice) never return
  a raw secret — `rotate_api_key` internally calls `create_api_key` for
  the new key (which does return its own raw secret, by design, exactly
  as the original `create_api_key` route does) but the OLD key's secret
  is never re-exposed.
- No `logger.*` call in `SecurityService.rotate_api_key`/`revoke_api_key`
  references a secret/token field.

## Webhook secrets

- `WebhookEndpoint.secret` (HMAC signing key) is returned once on
  `create_endpoint` (pre-existing, unchanged). `delete_endpoint` (closed
  this slice) never touches or logs the secret field.

## Document signing tokens

- `send_for_signature` (closed this slice) generates a `secrets.
  token_urlsafe(48)` signing token, stored on the `Document` row and
  returned in the response (by design — this is the URL/link the
  customer needs). No `logger.*` call in `send_for_signature` logs the
  token value.

## RAG / external provider credentials

- No LLM/embedding provider API key appears in any of the 11 routes'
  response payloads or `logger.*` calls (confirmed by reading `query`,
  `delete_kb`, `ingest_document`, `delete_document`, `reindex_document`
  in full — none references a provider credential; they are presumably
  configured via environment/settings, not read or logged in these
  methods).

## Conclusion

No secret/token/credential leakage found on any of the 11 routes closed
this slice.
