# Frozen Scope Verification - Slice 2F-31

| Set | Expected hash | Observed | Match | Count |
|---|---|---|---|---|
| A | 3a5124b153345df5 | 3a5124b153345df5 | YES | 9 |
| B | 62de4c311dde3043 | 62de4c311dde3043 | YES | 3 |
| C | 6d53d0647cdee7ec | 6d53d0647cdee7ec | YES | 7 |

All routes mounted, zero cross-set overlap. Canonical `fbe7cf863afa0d84`,
matrix `753653ed32916f4e` at start. Route lists loaded directly from the
Slice 2F-30 CSV files, never reconstructed from memory.

**Allow-list finding**: the implementation contract allow-lists
`app/engines/media/new_router.py`, `asset_service.py`, `access.py`, and
conditionally `service.py`. All 3 Set B routes live in `app/engines/media/
router.py` and are served by `app/engines/media/service.py::MediaService` -
a DIFFERENT service from the allow-listed `MediaAssetService`. Neither the
router nor (for these specific methods) the service is on the allow-list.
Documented rather than silently expanded.
