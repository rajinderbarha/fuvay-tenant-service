# M01 Non-Regression Report

No M01 (auth/identity/credential) file was touched by this slice.
`tests/test_phase2f29_m01_identity_closure.py` rebaselined for the
coverage-figure shift (264→273, 241→252, +9 Set B via 2F-35) and now
passes 43/43. Sample route `POST /v1/auth/api-keys` confirmed `VERIFIED`
throughout. `AuthService.revoke_api_key` (the separate, M01-closed
`api_keys` subsystem, distinct from `SecurityService`'s
`tenant_api_keys`) was confirmed still separate and untouched — see
[alternate-route-bypass-audit.csv](alternate-route-bypass-audit.csv).
