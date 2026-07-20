# Customer App — Dependency Decisions

## Added

| Package | Purpose | Alternative considered | Reason | Maintenance risk | Native-build impact | Bundle-size impact |
|---|---|---|---|---|---|---|
| `@tanstack/react-query` | Server-state caching/retry/dedup | Redux Toolkit Query | Smaller surface for a query-heavy, mutation-light app; no existing Redux store to extend | Low — widely used, active | None (JS-only) | ~13KB gzip |
| `zustand` | Foundation for future durable global client state | Redux Toolkit, React Context | Minimal boilerplate; this sprint uses dedicated Context providers instead (see `state-management-guidelines.md`) but the dependency is added now so a later sprint doesn't need a second PR just to add a state library | Low | None | ~1KB gzip |
| `react-hook-form` | Form primitive foundation for later sprints | Formik | Better RN performance (uncontrolled-first), smaller bundle, active maintenance | Low | None | ~9KB gzip |
| `zod` | Schema validation foundation | Yup | TypeScript-first inference, used across `pcat_*`/pricing backend patterns already familiar to this codebase's conventions | Low | None | ~13KB gzip (tree-shakeable) |
| `expo-secure-store` | Keychain-backed secure storage | react-native-keychain | Already inside the Expo SDK the app is pinned to (56); no extra native config needed for managed workflow | Low | None (Expo-managed) | native module, no JS bundle cost |
| `expo-localization` | System locale/RTL detection | react-native-localize | Same Expo-managed-workflow rationale as above | Low | None | native module |
| `i18next` + `react-i18next` | Localization framework | FormatJS/react-intl | Mature, namespace support matches the sprint's `common`/`showcase` namespace requirement, broad RN ecosystem examples | Low | None | ~15KB gzip |
| `jest`, `jest-expo` | Test runner | none needed — no test runner existed | Standard Expo-recommended Jest preset | Low | Dev-only | Dev-only |
| `@testing-library/react-native`, `@testing-library/jest-native`, `react-test-renderer` | Component testing | Enzyme (unmaintained for RN) | RNTL is the current RN-ecosystem standard, accessibility-first query API matches this sprint's a11y requirements | Low | Dev-only | Dev-only |
| `eslint`, `eslint-config-expo` | Linting | Custom flat config | No lint config existed at all; `eslint-config-expo` is the Expo-maintained baseline matching the app's SDK version | Low | Dev-only | Dev-only |
| `prettier` | Formatting | None existed | Needed for the `format:check` quality gate required by the sprint | Low | Dev-only | Dev-only |

## Removed

| Package | Reason |
|---|---|
| `@types/react-native` (devDependency) | Pinned to `^0.74.0`, which no longer resolves against the npm registry (the package was deprecated once `react-native` began shipping its own TypeScript types from 0.71+). `react-native@0.85.0` (already in `dependencies`) ships its own types, making this package both broken and redundant. Removing it was required just to get `npm install` to succeed — it was never functional in this repository state (no `node_modules` existed before this sprint). |

## Replaced

None — no existing library was swapped for an equivalent.

## Not Added (considered and rejected for this sprint)

- **`@react-native-community/netinfo`** — the connectivity foundation
  (`useConnectivity`) uses a lightweight reachability probe instead, to
  avoid adding a native module purely for a sprint that only needs an
  offline banner. Revisit if a later sprint needs granular connection-type
  data (wifi vs. cellular).
- **A bottom-sheet library** (`@gorhom/bottom-sheet`) — `BottomSheet.tsx`
  is a `Modal`-based implementation sufficient for this sprint's
  `showcase` demo; add a dedicated gesture-based sheet library only when a
  real feature needs drag-to-dismiss/snap-point behavior.
