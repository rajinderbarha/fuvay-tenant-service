# Signed Token / Key Redaction Report (WS6)

## Cloudinary credentials

`app/cloudinary_client.py`:
- `is_configured()` checks presence of `CLOUDINARY_CLOUD_NAME` /
  `CLOUDINARY_API_KEY` / `CLOUDINARY_API_SECRET` — booleans only, values
  never returned or logged.
- The upload signature (`hashlib.sha1((param_string +
  settings.CLOUDINARY_API_SECRET).encode()).hexdigest()`) uses the secret
  only as HMAC input; the secret itself is never placed in the returned
  `upload_params`, never logged.
- Verified: no `logger.*`/`log.*` call in this file references
  `API_SECRET`/`api_secret` (`tests/test_phase2f31a_n01_residual_closure.py
  ::TestStorageAuthority::test_cloudinary_secret_never_logged`, and R17 in
  `verify_n01_2f31a.py`).

## Signed delivery URLs / upload tokens

`app/engines/media/service.py::_signed_url` and `initiate_upload`'s
placeholder-mode `upload_url` both embed a `secrets.token_hex(...)` value in
the returned URL (this is by design — it IS the access token for that
asset). Neither is passed to `logger.info`/`logger.error` anywhere in
`service.py` — the only `logger` usage in this module predates this slice
and does not reference these values.

## Raw provider credentials

No S3/Cloudflare R2/Cloudinary access key or secret is returned in any
response payload from `MediaService` or `MediaStorageService` — only
derived signed URLs and upload params (which for Cloudinary include a
computed `signature`, not the secret itself, per Cloudinary's own signed
upload protocol).

## Conclusion

No signed-URL/token/credential leakage found on any of the 5 residual
routes or their supporting service code.
