# Customer App — State Management Guidelines

Four categories. Pick the narrowest one that fits.

## 1. Server State → TanStack Query

Anything that originates from the backend: bookings, jobs, pricing,
provider data, reviews, notifications. Use `src/state/query-client.ts`'s
`queryClient` (already provided at the root via `AppProviders`) with
`useQuery`/`useMutation`. Query keys follow the `queryKeys` factory
convention: `[domain, "detail", id]` / `[domain, "list", filters]`.

**Belongs here:** booking list, booking detail, price estimate, provider
profile, review list.

**Does not belong here:** anything that isn't fetched from the backend.

## 2. Global Client State → theme/locale/connectivity providers (or Zustand for future durable state)

Reserved for durable, app-wide, non-server state: resolved theme
preference (`ThemeProvider`), locale preference, connectivity status
(`useConnectivity`), dev-diagnostics toggles. `zustand` is added as a
dependency for this category but **no store is created in this sprint** —
the three examples above are implemented as dedicated React Context
providers/hooks instead, since each has exactly one consumer pattern and a
dedicated provider keeps the persistence/hydration logic colocated. Add a
Zustand store only when a genuinely cross-cutting piece of client state
needs to be read from many unrelated component trees without prop drilling
and a Context provider would mean wrapping large parts of the tree
unnecessarily.

**Belongs here:** theme preference, locale preference, "is the device
online" flag.

**Does not belong here:** a single screen's filter selection, a single
form's field values, anything server-fetched.

## 3. Feature State

State specific to one feature's workflow that outlives a single screen but
does not belong globally — e.g. an in-progress multi-step booking draft
that spans several screens. Lives in that feature's own `state/` folder
(e.g. `features/booking-draft/state/`) once that feature exists. Not
implemented in this sprint (booking is out of scope) — the convention is
documented here for the sprint that adds it.

**Belongs here:** a wizard's collected-so-far answers across steps.

**Does not belong here:** data already cached by TanStack Query — don't
duplicate server data into feature state; derive from the query result
instead.

## 4. Screen State → `useState`/`useReducer`

Local interaction state that only one screen or component cares about:
whether a modal is open, which tab is selected, the current value of a text
field before submit, scroll position.

**Belongs here:** "is this accordion expanded", a text field's live value,
whether a confirmation modal is visible.

**Does not belong here:** anything another screen needs to read.

## Anti-patterns to avoid

- Putting a form's field values in the global store "to be safe" — use
  local state or (later) React Hook Form.
- Re-fetching and hand-caching server data in `useState` instead of
  TanStack Query — loses caching/retry/dedup for free.
- Creating a new Zustand store per screen — that's screen state wearing a
  disguise.
