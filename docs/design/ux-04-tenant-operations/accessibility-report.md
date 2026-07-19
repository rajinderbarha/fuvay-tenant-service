# Accessibility Report

- `JobStatusTimeline` sets `aria-current="step"` on the active status.
- `SLAIndicator` puts the human-readable explanation in a `title` attribute
  (tooltip on hover/focus) rather than color alone conveying state; color
  is still the primary channel and no additional text label beyond the SLA
  label itself is rendered next to the dot — acceptable since the label
  text is always shown, not icon-only.
- No component uses raw hex colors; all colors reference design-system
  CSS custom properties (`var(--success-text)`, `var(--warning-text)`,
  etc.), inheriting whatever contrast guarantees those tokens provide.
- Keyboard/focus behavior was **not manually tested** this pass (no
  browser session was driven) — buttons in `AssignmentCandidateCard` and
  `PartsRequestSummary` are native `<button>` elements so they get default
  focus/keyboard activation, but no explicit focus-visible styling or
  keyboard-trap testing was performed.
- Screen-reader semantics beyond `aria-current` were not audited.
