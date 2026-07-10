/**
 * FRONTEND-CONNECT-01 — Response normalization helpers (super-admin).
 * Mirrors frontend/tenant-portal/lib/status-format.ts. Every value that
 * reaches JSX from an API response should pass through one of these —
 * never render null/undefined/NaN/a raw snake_case enum directly.
 */

export function safeNumber(v: unknown, fallback = 0): number {
  const n = typeof v === "number" ? v : typeof v === "string" ? Number(v) : NaN;
  return Number.isFinite(n) ? n : fallback;
}

export function safeText(v: unknown, fallback = "—"): string {
  if (v === null || v === undefined) return fallback;
  const s = String(v).trim();
  return s.length === 0 ? fallback : s;
}

export function safeBoolean(v: unknown, fallback = false): boolean {
  if (typeof v === "boolean") return v;
  if (v === "true") return true;
  if (v === "false") return false;
  return fallback;
}

export function safeCurrency(v: unknown, currency = "INR"): string {
  const n = safeNumber(v, 0);
  const symbol = currency === "INR" ? "₹" : currency + " ";
  return `${symbol}${n.toLocaleString("en-IN")}`;
}

export function safePrice(v: unknown, currency = "INR"): string {
  return safeCurrency(v, currency);
}

export function safePercent(v: unknown): string {
  const n = safeNumber(v, 0);
  return `${Math.max(0, Math.min(100, Math.round(n)))}%`;
}

export function safeDate(v: unknown, fallback = "—"): string {
  if (!v || typeof v !== "string") return fallback;
  const d = new Date(v);
  if (Number.isNaN(d.getTime())) return fallback;
  return d.toLocaleDateString("en-IN", { dateStyle: "medium" });
}

export function safeTime(v: unknown, fallback = "—"): string {
  if (!v || typeof v !== "string") return fallback;
  const d = new Date(v);
  if (Number.isNaN(d.getTime())) return fallback;
  return d.toLocaleString("en-IN", { dateStyle: "medium", timeStyle: "short" });
}

export function safeArray<T>(v: T[] | null | undefined): T[] {
  return Array.isArray(v) ? v : [];
}

export function safeRequestId(v: unknown): string | undefined {
  if (typeof v !== "string") return undefined;
  const s = v.trim();
  return s.length === 0 ? undefined : s;
}

const STATUS_LABELS: Record<string, string> = {
  bookable: "Bookable", not_bookable: "Not Bookable", visible: "Visible", not_visible: "Not Visible",
  pending_setup: "Pending Setup", approved: "Approved", active: "Active", inactive: "Inactive",
  pending: "Pending", pending_review: "Under Review", expired: "Expired", rejected: "Rejected",
  cancelled: "Cancelled", draft: "Draft", suspended: "Suspended", blocked: "Blocked",
  completed: "Completed", in_progress: "In Progress", assigned: "Assigned", unassigned: "Unassigned",
  customer_pays_provider_directly: "Customer Pays Provider Directly",
};

/** Formats a raw status/enum string for display. Falls back to Title Case of the raw value. */
export function safeStatus(v: unknown, fallback = "Unknown"): string {
  if (v === null || v === undefined) return fallback;
  const key = String(v).trim();
  if (key.length === 0) return fallback;
  return STATUS_LABELS[key] ?? key.replace(/_/g, " ").replace(/\b\w/g, (c) => c.toUpperCase());
}
