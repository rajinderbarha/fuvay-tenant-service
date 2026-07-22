# Environment Test Evidence - Slice 2F-29

api:8000, postgres:5432, redis:6379 - REACHABLE at slice start and unchanged
throughout. No test was attributed to an environment change: the suite was
green (2170 passed) before the slice and green after (2213 passed, which
includes this slice's 43 new M01 tests), with the only movement
being the intended M01 status changes and their rebaselined assertions.
