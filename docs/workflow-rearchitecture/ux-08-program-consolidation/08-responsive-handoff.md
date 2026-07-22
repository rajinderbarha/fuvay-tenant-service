# UX-08 Workstream 19: Responsive / Pixel-Width Handoff

Status: `NOT_EXECUTED_IN_UX08` / `DEFERRED_DUE_TO_PLANNED_DESIGN_REPLACEMENT`
— per the UX-08 brief's explicit, non-negotiable instruction: "Do NOT claim
responsive certification — everything pixel-width-related is DEFERRED_DUE_
TO_PLANNED_DESIGN_REPLACEMENT, full stop." This is a formalization of
guidance the user separately gave mid-UX-07 (responsive work now would be
wasted since the design will change).

## What was explicitly NOT done this pass

- No viewport/breakpoint testing across any app.
- No pixel-width certification of any screen, in any app, at any breakpoint.
- No new responsive CSS/layout work of any kind.
- No screenshot-based visual regression pass (see doc 10/12 for what visual
  evidence WAS reused/cited from prior phases, which is distinct from new
  responsive certification).

## Why

1. The user has already directed that responsive work is premature ahead of
   a planned design replacement — spending UX-08 time on it would be work
   thrown away at the next real redesign.
2. UX-08's own scope is explicitly non-redesign, verification/consolidation
   only — pixel-level work would also exceed the "small, evidence-backed
   correctness fixes only" mandate for any code changes.

## Disposition for every app

| App | Responsive/pixel status |
|---|---|
| Customer App | `DEFERRED_DUE_TO_PLANNED_DESIGN_REPLACEMENT` |
| Super Admin | `DEFERRED_DUE_TO_PLANNED_DESIGN_REPLACEMENT` |
| Tenant Portal | `DEFERRED_DUE_TO_PLANNED_DESIGN_REPLACEMENT` |
| Staff/Technician App | `DEFERRED_DUE_TO_PLANNED_DESIGN_REPLACEMENT` |

## What the next redesign pass should do instead

Treat doc 07 (functional contract handoff) as the input, design new
responsive layouts against those functional contracts, and run a real
pixel/breakpoint certification pass ONCE against the new design — not
against the current one, which is expected to be replaced.
