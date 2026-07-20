# Frontend File Allow-List (what this phase touched)

All paths relative to repo root, all under the two allowed roots:

## mobile/staff-app/
- `package.json`, `package-lock.json` (new)
- `src/types/ux05.ts` (new)
- `src/types/__tests__/provenance.test.ts` (new)
- `src/lib/ux05/permissions.ts` (new)
- `src/lib/ux05/__tests__/permissions.test.ts` (new)
- `src/components/ux05/PipelineBadge.tsx`, `PermissionRestrictedState.tsx`, `NextActionBar.tsx`,
  `PartsRequestStatusCard.tsx` (new)
- `src/screens/ux05/PartsRequestShowcaseScreen.tsx` (new)

## docs/design/ux-05-staff-technician-app/
This documentation subset (see `deferred-items.md` for the full 72-file target vs. what was written).

No file under `frontend/packages/design-system` was touched (it is unused by this app — confirmed, see
`execution-environment.md`).
