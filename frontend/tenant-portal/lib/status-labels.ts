/**
 * Sprint 34A — Centralized status label definitions.
 * Maps technical status strings to human-readable labels and visual variants.
 *
 * Usage:
 *   import { JOB_STATUS, BOOKING_STATUS } from "@/lib/status-labels";
 *   const { label, variant } = JOB_STATUS[job.status] ?? JOB_STATUS._default;
 */

export interface StatusDef {
  label: string;
  variant: "success" | "warning" | "danger" | "info" | "muted" | "default" | "golden" | "terra";
  description?: string;
}

// ── Account / User ────────────────────────────────────────────────────────────
export const ACCOUNT_STATUS: Record<string, StatusDef> = {
  active:              { label: "Active",              variant: "success" },
  locked:              { label: "Locked",              variant: "danger" },
  disabled:            { label: "Disabled",            variant: "muted" },
  suspended:           { label: "Suspended",           variant: "danger" },
  pending_activation:  { label: "Pending Activation",  variant: "warning" },
  _default:            { label: "Unknown",             variant: "muted" },
};

export const USER_ROLE: Record<string, StatusDef> = {
  super_admin:    { label: "Super Admin",    variant: "golden" },
  tenant_owner:   { label: "Business Owner", variant: "info" },
  staff:          { label: "Staff",          variant: "default" },
  customer:       { label: "Customer",       variant: "muted" },
  _default:       { label: "User",           variant: "muted" },
};

// ── Tenant / Provider ─────────────────────────────────────────────────────────
export const TENANT_STATUS: Record<string, StatusDef> = {
  active:              { label: "Active",           variant: "success" },
  pending_verification:{ label: "Pending Review",   variant: "warning" },
  suspended:           { label: "Suspended",        variant: "danger" },
  rejected:            { label: "Rejected",         variant: "danger" },
  deactivated:         { label: "Deactivated",      variant: "muted" },
  onboarding:          { label: "Onboarding",       variant: "info" },
  _default:            { label: "Unknown",          variant: "muted" },
};

export const VERIFICATION_STATUS: Record<string, StatusDef> = {
  not_started:         { label: "Not Started",     variant: "muted" },
  pending:             { label: "Pending Review",  variant: "warning" },
  in_review:           { label: "In Review",       variant: "info" },
  approved:            { label: "Approved",        variant: "success" },
  rejected:            { label: "Rejected",        variant: "danger" },
  requires_resubmit:   { label: "Needs Update",    variant: "warning" },
  _default:            { label: "Unknown",         variant: "muted" },
};

// ── Bookings ──────────────────────────────────────────────────────────────────
export const BOOKING_STATUS: Record<string, StatusDef> = {
  pending:             { label: "Pending",          variant: "warning" },
  confirmed:           { label: "Confirmed",        variant: "success" },
  cancelled:           { label: "Cancelled",        variant: "muted" },
  rejected:            { label: "Rejected",         variant: "danger" },
  completed:           { label: "Completed",        variant: "success" },
  rescheduled:         { label: "Rescheduled",      variant: "info" },
  voided:              { label: "Voided",           variant: "muted" },
  no_show:             { label: "No Show",          variant: "danger" },
  in_progress:         { label: "In Progress",      variant: "info" },
  _default:            { label: "Unknown",          variant: "muted" },
};

// ── Jobs ──────────────────────────────────────────────────────────────────────
export const JOB_STATUS: Record<string, StatusDef> = {
  pending_assignment:  { label: "Pending Assignment", variant: "warning" },
  assigned:            { label: "Assigned",           variant: "info" },
  staff_accepted:      { label: "Staff Accepted",     variant: "info" },
  staff_en_route:      { label: "En Route",           variant: "info" },
  staff_arrived:       { label: "Arrived",            variant: "info" },
  in_progress:         { label: "In Progress",        variant: "info" },
  diagnosis_done:      { label: "Diagnosis Done",     variant: "info" },
  awaiting_quote:      { label: "Awaiting Quote",     variant: "warning" },
  quote_sent:          { label: "Quote Sent",         variant: "warning" },
  quote_approved:      { label: "Quote Approved",     variant: "success" },
  quote_rejected:      { label: "Quote Rejected",     variant: "danger" },
  parts_sourcing:      { label: "Parts Sourcing",     variant: "warning" },
  parts_sourced:       { label: "Parts Sourced",      variant: "info" },
  checklist_pending:   { label: "Checklist Pending",  variant: "warning" },
  checklist_done:      { label: "Checklist Done",     variant: "success" },
  completion_review:   { label: "Completion Review",  variant: "warning" },
  completed:           { label: "Completed",          variant: "success" },
  cancelled:           { label: "Cancelled",          variant: "muted" },
  voided:              { label: "Voided",             variant: "muted" },
  disputed:            { label: "Disputed",           variant: "danger" },
  awaiting_payment:    { label: "Awaiting Payment",   variant: "warning" },
  paid:                { label: "Paid",               variant: "success" },
  rework_required:     { label: "Rework Required",    variant: "danger" },
  resumed:             { label: "Resumed",            variant: "info" },
  _default:            { label: "Unknown",            variant: "muted" },
};

// ── Payments / Invoices ───────────────────────────────────────────────────────
export const PAYMENT_STATUS: Record<string, StatusDef> = {
  pending:             { label: "Pending",          variant: "warning" },
  processing:          { label: "Processing",       variant: "info" },
  completed:           { label: "Paid",             variant: "success" },
  failed:              { label: "Failed",           variant: "danger" },
  refunded:            { label: "Refunded",         variant: "muted" },
  partially_refunded:  { label: "Partial Refund",   variant: "warning" },
  voided:              { label: "Voided",           variant: "muted" },
  _default:            { label: "Unknown",          variant: "muted" },
};

export const INVOICE_STATUS: Record<string, StatusDef> = {
  draft:               { label: "Draft",            variant: "muted" },
  issued:              { label: "Issued",           variant: "info" },
  paid:                { label: "Paid",             variant: "success" },
  overdue:             { label: "Overdue",          variant: "danger" },
  voided:              { label: "Voided",           variant: "muted" },
  _default:            { label: "Unknown",          variant: "muted" },
};

// ── Complaints / Disputes ─────────────────────────────────────────────────────
export const COMPLAINT_STATUS: Record<string, StatusDef> = {
  open:                { label: "Open",             variant: "warning" },
  in_review:           { label: "Under Review",     variant: "info" },
  escalated:           { label: "Escalated",        variant: "danger" },
  resolved:            { label: "Resolved",         variant: "success" },
  dismissed:           { label: "Dismissed",        variant: "muted" },
  _default:            { label: "Unknown",          variant: "muted" },
};

// ── Reviews ───────────────────────────────────────────────────────────────────
export const REVIEW_STATUS: Record<string, StatusDef> = {
  pending:             { label: "Pending",          variant: "warning" },
  published:           { label: "Published",        variant: "success" },
  flagged:             { label: "Flagged",          variant: "danger" },
  removed:             { label: "Removed",          variant: "muted" },
  _default:            { label: "Unknown",          variant: "muted" },
};

// ── Staff ─────────────────────────────────────────────────────────────────────
export const STAFF_STATUS: Record<string, StatusDef> = {
  active:              { label: "Active",           variant: "success" },
  on_leave:            { label: "On Leave",         variant: "warning" },
  inactive:            { label: "Inactive",         variant: "muted" },
  suspended:           { label: "Suspended",        variant: "danger" },
  _default:            { label: "Unknown",          variant: "muted" },
};

// ── Helper ────────────────────────────────────────────────────────────────────
/** Get a status definition with fallback to _default or unknown. */
export function getStatus(
  map: Record<string, StatusDef>,
  key: string | null | undefined,
): StatusDef {
  if (key && map[key]) return map[key];
  return map._default ?? { label: key ?? "Unknown", variant: "muted" };
}
