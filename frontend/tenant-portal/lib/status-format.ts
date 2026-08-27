// Safe formatters + status label maps for the Tenant My Status
// (Provider Visibility & Bookability) page. No null/undefined/NaN/raw-enum
// should ever reach JSX — every value shown on that page goes through one of
// these first.

export function safeNum(v: unknown, fallback = 0): number {
  const n = typeof v === "number" ? v : typeof v === "string" ? Number(v) : NaN;
  return Number.isFinite(n) ? n : fallback;
}

export function safeText(v: unknown, fallback = "—"): string {
  if (v === null || v === undefined) return fallback;
  const s = String(v).trim();
  return s.length === 0 ? fallback : s;
}

export function safeCurrency(v: unknown, currency = "INR"): string {
  const n = safeNum(v, 0);
  const symbol = currency === "INR" ? "₹" : currency + " ";
  return `${symbol}${n.toLocaleString("en-IN")}`;
}

export function safePercent(v: unknown): string {
  const n = safeNum(v, 0);
  return `${Math.max(0, Math.min(100, Math.round(n)))}%`;
}

export function safeDate(v: unknown, fallback = "Never"): string {
  if (!v || typeof v !== "string") return fallback;
  const d = new Date(v);
  if (Number.isNaN(d.getTime())) return fallback;
  return d.toLocaleString("en-IN", { dateStyle: "medium", timeStyle: "short" });
}

export function safeArray<T>(v: T[] | null | undefined): T[] {
  return Array.isArray(v) ? v : [];
}

// FRONTEND-CONNECT-01 additions ------------------------------------------

/** Alias of safeNum kept for naming parity with the super-admin normalize.ts module. */
export function safeNumber(v: unknown, fallback = 0): number {
  return safeNum(v, fallback);
}

export function safeBoolean(v: unknown, fallback = false): boolean {
  if (typeof v === "boolean") return v;
  if (v === "true") return true;
  if (v === "false") return false;
  return fallback;
}

export function safePrice(v: unknown, currency = "INR"): string {
  return safeCurrency(v, currency);
}

export function safeTime(v: unknown, fallback = "—"): string {
  if (!v || typeof v !== "string") return fallback;
  const d = new Date(v);
  if (Number.isNaN(d.getTime())) return fallback;
  return d.toLocaleString("en-IN", { dateStyle: "medium", timeStyle: "short" });
}

export function safeRequestId(v: unknown): string | undefined {
  if (typeof v !== "string") return undefined;
  const s = v.trim();
  return s.length === 0 ? undefined : s;
}

const STATUS_LABELS: Record<string, string> = {
  bookable: "Bookable",
  not_bookable: "Not bookable",
  visible: "Visible",
  not_visible: "Not visible",
  pending_setup: "Pending setup",
  approved: "Approved",
  active: "Active",
  inactive: "Inactive",
  no_subscription: "No active package",
  received: "Received",
  waived: "Waived",
  paid: "Received",
  unpaid: "Pending",
  pending: "Pending",
  not_initialized: "Not yet set up",
  refunded: "Refunded",
  forfeited: "Forfeited",
  selected: "Selected",
  pending_review: "Under review",
  pending_payment: "Payment pending",
  paid_pending_approval: "Awaiting admin approval",
  expired: "Expired",
  rejected: "Rejected",
  cancelled: "Cancelled",
  draft: "Draft",
  suspended: "Suspended",
  blocked: "Blocked",
};

export function safeStatus(v: unknown, fallback = "Unknown"): string {
  if (v === null || v === undefined) return fallback;
  const key = String(v).trim();
  if (key.length === 0) return fallback;
  return STATUS_LABELS[key] ?? key.replace(/_/g, " ").replace(/\b\w/g, c => c.toUpperCase());
}

export type Severity = "critical" | "warning" | "info";

export interface RequiredAction {
  code: string;
  severity: Severity;
  title: string;
  reason: string;
  cta: string;
  route: string;
  ruleKey: string;
}

const BLOCKER_TYPE_META: Record<string, { title: string; cta: string; route: string; ruleKey: string; severity: Severity }> = {
  business_profile_incomplete: { title: "Business Profile Incomplete", cta: "Complete Business Profile", route: "/profile", ruleKey: "business_profile_complete", severity: "warning" },
  package_inactive:            { title: "Finance Setup Incomplete", cta: "Open Finance", route: "/home-services/finance", ruleKey: "finance_ready", severity: "critical" },
  usage_credits_missing:       { title: "No Usage Credits Available", cta: "Buy Usage Credits", route: "/home-services/finance?tab=usage-credits", ruleKey: "usage_credits_available", severity: "critical" },
  technician_seats_pending:    { title: "Technician Seats Needed", cta: "Buy a top-up plan", route: "/home-services/finance", ruleKey: "topup_plan.seat_entitlement", severity: "critical" },
  service_area_missing:        { title: "No Coverage Pincode Configured", cta: "Configure Coverage", route: "/business/coverage-hours", ruleKey: "service_area_active", severity: "critical" },
  service_missing:             { title: "No Service Offering Enabled", cta: "Enable an Offering", route: "/home-services/services", ruleKey: "offering_active", severity: "critical" },
  coverage_missing:            { title: "Service Coverage Not Configured", cta: "Configure Services", route: "/home-services/services", ruleKey: "coverage_configured", severity: "warning" },
  active_technician_missing:   { title: "No Active Technician", cta: "Add Technician", route: "/home-services/team", ruleKey: "active_technician_present", severity: "critical" },
  availability_missing:        { title: "Availability Not Configured", cta: "Set Availability", route: "/home-services/availability", ruleKey: "availability_configured", severity: "warning" },
  documents_pending:           { title: "Documents Pending", cta: "View Documents", route: "/documents", ruleKey: "documents_verified", severity: "warning" },
  pricing_setup_missing:       { title: "Pricing Not Configured", cta: "Manage Pricing", route: "/home-services/services", ruleKey: "pricing_valid", severity: "warning" },
  tenant_not_approved:         { title: "Tenant Not Yet Approved", cta: "View Business Profile", route: "/profile", ruleKey: "tenant_approved", severity: "critical" },
  tenant_suspended:            { title: "Tenant Suspended", cta: "Contact Support", route: "/profile", ruleKey: "tenant_not_suspended", severity: "critical" },
};

export function blockerMeta(code: string) {
  const normalizedCode = code.trim().toLowerCase();
  return BLOCKER_TYPE_META[normalizedCode] ?? {
    title: code.replace(/_/g, " ").replace(/\b\w/g, c => c.toUpperCase()),
    cta: "Review",
    route: "/profile",
    ruleKey: normalizedCode,
    severity: "warning" as Severity,
  };
}
