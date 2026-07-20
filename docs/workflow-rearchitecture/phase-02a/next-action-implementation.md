# Next-Action Foundation Implementation

## Status: NOT implemented this phase

The chosen vertical slice (My Work + Parts Request/Approval for the technician role) did not require a separate, reusable Next-Action panel component — the My Work page's per-item `recommended_action` / `available_actions` / `primary_action` fields (see `my-work-implementation.md`) already surface next-action-shaped information inline, and the job detail page's existing `NEXT_ACTIONS` status-to-button map (predating this phase) already serves the same purpose for a single job's detail view.

## Why this was deferred rather than partially built
Workstream 5 asks for a **reusable** backend + frontend next-action model spanning 8 domains (Business onboarding, Business approval, Provider setup, Quote, Parts request, Finance risk, Compliance request, Security incident). Building a generic contract and panel component for only 1 of those 8 domains (Parts request, the only one this phase touches) would either:
- produce an abstraction with a single caller (premature generalization), or
- require touching business-onboarding/approval/compliance/security code that is entirely out of this phase's scope.

Both outcomes conflict with the "one real vertical slice, fully working" scope decision. The Parts Request UI in this phase instead surfaces next-action information directly and concretely (status badges, inline recommended actions) without a generic contract layer.

## What a future phase would need
Per `next-action-contract.md` (Phase 1A), the reusable contract's 15 fields and 4 source-type labels are already specified and did not need rework. A future phase should implement the shared backend response builder and frontend panel component once at least 2-3 of the 8 domains are ready to consume it, to avoid the single-caller abstraction problem above.
