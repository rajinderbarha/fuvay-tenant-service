# M01 Non-Regression Report

No M01 (auth/identity/credential) file was touched by this slice.
`tests/test_phase2f29_m01_identity_closure.py` was rebaselined for the
denominator/protected-count shift (262→264, 238→241, both attributable
entirely to this slice's Set B additions, not to any M01 change) and now
passes 43/43. Sample route `POST /v1/auth/api-keys` confirmed `VERIFIED`
throughout.
