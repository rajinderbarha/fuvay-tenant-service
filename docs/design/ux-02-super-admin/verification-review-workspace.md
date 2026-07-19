# Verification Review Workspace

Component: `ReviewApprovalWorkspace` (`components/ux02/patterns/ReviewApprovalWorkspace.tsx`),
instantiated at `/dev/ux-02/verification`. Readiness: `MOCK_DESIGN_ONLY`.

## Layout
Two-column: left column (Applicant Summary, Checklist, Documents), right column (Decision panel),
matching the spec's "full workspace, not a small modal" requirement.

## Documents
Rendered as `[secure preview placeholder, token-gated]` labels only — never a raw storage key or
signed URL, per hard constraint. The real component takes a caller-supplied document list
(`{id, label}`) and does not accept or render arbitrary URLs.

## Decision panel
- Reason textarea (required to enable Reject).
- Three actions: Approve, Request More Info, Reject.
- Clicking an action opens an inline `role="alertdialog"` confirmation (Confirm / Cancel) — no
  action fires on first click.
- On confirm, an `onDecision` callback fires and a "(design-only — no backend call)" message is
  shown. No backend mutation occurs.

## Reuse
Same component powers the Compliance Case resolution flow (`/dev/ux-02/compliance/[id]`) — this is
the one reusable review/approval pattern required by the task spec, used in 2 places.
