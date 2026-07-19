# Review / Approval Pattern

Component: `frontend/super-admin/components/ux02/patterns/ReviewApprovalWorkspace.tsx`. Full page
workspace, not a modal, per hard constraint.

## Used by
Verification Review (`/dev/ux-02/verification`), Compliance Case resolution
(`/dev/ux-02/compliance/[id]`) — 2 usages.

## Props contract
`title`, `summary: ReactNode`, `checklist: {id,label,status}[]`, `documents: {id,label}[]`,
`onDecision?(decision, reason)`.

## Decision flow
1. User types a reason (required to enable Reject).
2. Clicking Approve/Request More Info/Reject sets a `pendingDecision`, rendering an inline
   `role="alertdialog"` confirmation — never fires on first click.
3. Confirm invokes `onDecision` and shows a "(design-only — no backend call)" success message;
   Cancel clears the pending state.

## Documents
Fixture-token labels only, `[secure preview placeholder, token-gated]` — no raw storage keys or
signed URLs ever rendered, matching the hard constraint on verification documents.
