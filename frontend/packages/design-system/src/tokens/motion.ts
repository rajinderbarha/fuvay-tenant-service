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
} as const;

export type StatusKey = keyof typeof statusRegistry;
export type Tone = "success" | "warning" | "danger" | "info" | "neutral" | "brand";
