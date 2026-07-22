# Baseline Freeze Evidence - Slice 2F-29

Frozen before any code change:
- Set A `012100a703047743`, Set B `f1acd7b43c669b9e`, Set C `c77889cac83f07be`
- canonical `e7a89231207221aa`, matrix `ee6011f6ce6a97ab`
- environment: api:8000, postgres:5432, redis:6379 all REACHABLE
- exact failing node IDs before the slice: **none** (suite green at 2170)

After all writes:
- canonical `fbe7cf863afa0d84`, matrix `753653ed32916f4e`
- application files changed: exactly 2 (`app/engines/auth/router.py`,
  `app/engines/auth/service.py`)
