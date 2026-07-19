# Lockfile and Toolchain Evidence

- `frontend/tenant-portal/package.json`: `"react"`/`"react-dom"` changed
  from exact `"19.2.0"` to exact `"19.2.7"` (see
  `four-failure-root-cause-report.md`).
- `frontend/tenant-portal/package-lock.json`: a stray nested lockfile
  tracked in git since the original repo baseline commit `36efe8d`
  (predates UX-01). Confirmed this pass that its presence does NOT block
  the react-version fix from taking effect once `package.json`'s pin
  itself is corrected — `npm install` re-resolves and updates the nested
  lockfile's pinned react entry to match the new `package.json` range/pin
  once the pin changes (verified via `require.resolve('react', {paths:
  [...]})` returning the hoisted root path after reinstall). The stray
  lockfile file itself was left as-is (not deleted) — deleting it is a
  separate, larger toolchain-hygiene decision (it also exists for
  `frontend/super-admin`, which is out of scope to touch) better handled
  in one dedicated pass across both workspaces rather than half-fixed
  here.
- No change to the root `package.json`'s `workspaces` field or to any
  other workspace's `package.json`.
