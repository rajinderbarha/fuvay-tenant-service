# Verifier Negative Fixture Report

`verify_2f37.py --selftest`: 21/21 "fires when violated", reconfirmed.

`test_phase2f39a2_security_apikey_fix.py`'s own negative fixtures: missing
tenant context is proven to reject before the request body is even
parsed (`FakeRequest.json()` raises `AssertionError` if called, proving
the guard short-circuits first); a spoofed body tenant_id is proven
ignored (asserted equal to the caller's real tenant, not the spoofed one).
