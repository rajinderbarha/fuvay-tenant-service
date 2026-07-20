# Test Quality Report - Slice 2F-27A

- The change-guard asserts EXACTLY two routes added, both unprotected, new
  hashes, 259/214/45, no unauthorized candidate, and (positively) that
  historical docs are preserved and the hold registry excludes both authorized
  routes.
- Rebaselining touched only current executable assertions; a dedicated test
  (TestHistoricalDocsPreserved) proves the 2F-26H hash doc and 2F-27 BLOCKED
  status were NOT rewritten.
