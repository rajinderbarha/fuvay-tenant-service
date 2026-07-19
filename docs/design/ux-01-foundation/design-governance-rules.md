# Design Governance Rules

1. **No raw hex/rgb colors in feature or component code.** Always reference
   a semantic CSS var (`var(--brand)`, etc.) or a `colorVar`/`chartPalette`
   export from `@serviceos/design-system`. Chart series colors are the one
   sanctioned exception (documented in `design-token-specification.md`).
2. **No new status outside the registry.** Any new lifecycle status
   (booking, complaint, compliance, invoice, etc.) must be added to
   `statusRegistry` in `tokens/motion.ts` before a page renders it via
   `StatusBadge` — do not hand-roll a one-off colored pill.
3. **No custom modal/dialog implementations.** Use `Modal`/`Drawer` from the
   design system so focus-trap/Escape/ARIA behavior stays consistent and
   centrally fixable.
4. **Icon-only controls must set `aria-label`.** Enforced with a dev-time
   console warning in `Button`.
5. **Typography via `.ds-text-*` classes**, not ad-hoc `font-size` values,
   for any new shared component.
6. **Respect reduced motion** — any new animation must either use the
   `--motion-*` duration vars (which the global reduced-motion media query
   already zeroes) or check `motionDuration()` if driven from JS.
7. **New shared UI belongs in the package**, not duplicated per-app. If a
   component is needed in both `super-admin` and `tenant-portal`, add it to
   `frontend/packages/design-system`, not copy-pasted.
