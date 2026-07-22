# Deferred Items

- Resolve the 21 `PRODUCT_DECISION_REQUIRED` routes — prioritize the ~8
  bare-`require_permission` instances first (matches a confirmed real
  defect pattern twice already), then the ~13 bare-`get_current_user`
  instances.
- N01 media routes remain deferred to N01's own remediation track,
  unchanged.
- A dedicated `verify_2f39a3.py`.
- A second full-backend-regression run.
- A systematic read-path privacy scan across the ~1,134 non-mutation
  routes (distinct from and larger than this program's mutation-only
  scope to date).
- All items already deferred by 2F-39/2F-39A/2F-39A2/2F-39A2R remain
  deferred, unchanged.
