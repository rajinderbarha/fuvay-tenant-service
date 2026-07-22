# Closed-Module Canary Report

Re-ran the closest non-regression canaries to this slice's changes:

- `tests/test_phase2f29_m01_identity_closure.py`: 43/43
- `tests/test_phase2f31_n01_media_closure.py`: 34/34
- `tests/test_phase2f31a_n01_residual_closure.py`: 30/30
- `tests/test_phase2f33_geo_zone_closure.py`: 25/25
- `tests/test_phase2f28_module_selection.py`: 34/34
- `tests/test_phase2f30_post_m01_selection.py`: 42/42

All pass. No previously-closed module regressed.
