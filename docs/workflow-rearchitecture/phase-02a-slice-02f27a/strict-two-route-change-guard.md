# Strict Two-Route Change Guard - Slice 2F-27A

tests/test_phase2f27a_two_route_expansion.py enforces:
- both authorized routes present; denominator 259; protected 214; unprotected 45
- no duplicate route keys; no unauthorized candidate present
- both rows PERMISSION_ONLY_NOT_SCOPE_AWARE (not FULLY_PROTECTED); 2F-27A provenance
- both matrix module rows present and unprotected
- new canonical + matrix hashes
- all 59 mixed-persona candidates held; neither authorized route in the hold registry
- historical docs preserved (2F-26H still records old hash; 2F-27 still BLOCKED)
