export const duration = {
  instant: 80,
  fast: 150,
  base: 220,
  slow: 320,
} as const;

export const easing = {
  standard: "cubic-bezier(0.2, 0, 0, 1)",
  decelerate: "cubic-bezier(0, 0, 0.2, 1)",
  accelerate: "cubic-bezier(0.3, 0, 1, 1)",
} as const;

/** Returns 0 when the user prefers reduced motion, else the given ms. Safe to
 * call during SSR (defaults to reduced=false). */
export function motionDuration(ms: number): number {
  if (typeof window === "undefined" || !window.matchMedia) return ms;
  return window.matchMedia("(prefers-reduced-motion: reduce)").matches ? 0 : ms;
}

export const statusRegistry = {
  active: { tone: "success", label: "Active" },
  approved: { tone: "success", label: "Approved" },
  completed: { tone: "success", label: "Completed" },
  pending: { tone: "warning", label: "Pending" },
  in_review: { tone: "warning", label: "In Review" },
  scheduled: { tone: "info", label: "Scheduled" },
  in_progress: { tone: "info", label: "In Progress" },
  rejected: { tone: "danger", label: "Rejected" },
  cancelled: { tone: "danger", label: "Cancelled" },
  failed: { tone: "danger", label: "Failed" },
  suspended: { tone: "danger", label: "Suspended" },
  draft: { tone: "neutral", label: "Draft" },
  archived: { tone: "neutral", label: "Archived" },
  expired: { tone: "neutral", label: "Expired" },

  // Additive — DESIGN PHASE UX-03 (tenant portal). Purely new keys, no
  // existing key changed/removed, so this cannot alter Super Admin (UX-02)
  // rendering; verified by re-reading every existing key above unchanged.
  not_started: { tone: "neutral", label: "Not Started" },
  ready_to_submit: { tone: "info", label: "Ready to Submit" },
  submitted: { tone: "warning", label: "Submitted" },
  under_review: { tone: "warning", label: "Under Review" },
  changes_requested: { tone: "warning", label: "Changes Requested" },
  requested: { tone: "info", label: "Requested" },
  confirmed: { tone: "info", label: "Confirmed" },
  quoted: { tone: "info", label: "Quoted" },
  awaiting_parts: { tone: "warning", label: "Awaiting Parts" },
  installed: { tone: "success", label: "Installed" },
  granted_by_role: { tone: "success", label: "Granted (Role Default)" },
  granted_override: { tone: "success", label: "Granted (Override)" },
  denied_override: { tone: "danger", label: "Denied (Explicit)" },
  not_granted: { tone: "neutral", label: "Not Granted" },
  invited: { tone: "info", label: "Invited" },
  inactive: { tone: "neutral", label: "Inactive" },
  covered: { tone: "success", label: "Covered" },
  partial: { tone: "warning", label: "Partial Coverage" },
  not_covered: { tone: "neutral", label: "Not Covered" },
  conflict: { tone: "danger", label: "Conflict" },
  held: { tone: "info", label: "Held" },
  released: { tone: "success", label: "Released" },
  forfeited: { tone: "danger", label: "Forfeited" },
  escalated_to_platform: { tone: "danger", label: "Escalated to Platform" },
  expiring_soon: { tone: "warning", label: "Expiring Soon" },
  not_submitted: { tone: "neutral", label: "Not Submitted" },
} as const;

export type StatusKey = keyof typeof statusRegistry;
export type Tone = "success" | "warning" | "danger" | "info" | "neutral" | "brand";
