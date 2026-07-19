# Global Search / Command Palette Specification

Nav entry: `ux02-search` in `lib/ux02/nav-ia.ts` — `readiness: API_CONTRACT_REQUIRED`,
`readOnlyBehavior: visible_disabled`, `mobileBehavior: hidden_on_mobile`.

## Adapter interface (typed, not connected)
```ts
export interface CommandPaletteAdapter {
  search(query: string): Promise<{ id: string; label: string; group: string; href: string }[]>;
}
```
(defined in `lib/ux02/types.ts`)

## Status
No unified cross-domain search endpoint exists on the backend today (confirmed by absence of any
such route in the engines reviewed for this phase). The palette shell is a typed interface only;
building the UI chrome (input, results list, keyboard nav) is deferred to when a real adapter can
be wired — see `deferred-items.md` and `backend-contract-dependencies.md`. Do not build a client-side
fuzzy-search-over-fixtures palette and present it as functional; that would misrepresent readiness.

## Keyboard/interaction contract (for the future implementation)
- Open: Cmd/Ctrl+K.
- Arrow keys navigate results, Enter activates, Escape closes.
- Grouped results by domain (Tenants, Compliance, Audit, Settings).
