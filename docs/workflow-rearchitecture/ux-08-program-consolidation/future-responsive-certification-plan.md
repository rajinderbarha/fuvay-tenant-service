# Future Responsive Certification Plan

**All items below are marked `NOT_EXECUTED_IN_UX08`.**
**Reason: `DEFERRED_DUE_TO_PLANNED_DESIGN_REPLACEMENT`.**

This is a deliberate scope decision (explicit user direction during UX-07:
certifying exact pixel-width layouts before the Customer visual design is
replaced would be wasted effort), not a defect or an incomplete
verification.

## Future required widths

320px, 360px, 390px, 430px, 768px, 1024px — all `NOT_EXECUTED_IN_UX08`.

## Future required checks (all `NOT_EXECUTED_IN_UX08`)

- No horizontal overflow
- No clipped action
- Keyboard safety
- Safe areas
- Long Hindi and Punjabi text wrapping
- Bottom navigation
- Dialogs
- Bottom sheets
- Address wrapping
- Price layouts
- Text scaling

## When to execute this plan

After the future Customer design-replacement phase delivers a stable
visual design, re-run this plan in full against the new implementation,
using `customer-redesign-handoff.md`'s functional contracts as the
correctness baseline (the new design must satisfy the same functional
requirements, at whatever new visual layout it uses).
