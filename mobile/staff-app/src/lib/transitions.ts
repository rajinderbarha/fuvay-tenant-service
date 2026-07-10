/**
 * VALID_TRANSITIONS — job status state machine.
 * Staff-specific: only staff-actionable transitions included.
 * Mirrors the tenant portal graph — single source of truth.
 */
export const VALID_TRANSITIONS: Record<string, string[]> = {
  assigned:       ["accepted",  "cancelled"],
  accepted:       ["en_route",  "cancelled"],
  en_route:       ["arrived",   "cancelled"],
  arrived:        ["in_progress"],
  in_progress:    ["parts_required", "quality_check", "completed"],
  parts_required: ["parts_sourced"],
  parts_sourced:  ["resumed"],
  resumed:        ["quality_check", "completed"],
  quality_check:  ["completed", "in_progress"],
  completed:      [],
};

export const SLA_BANDS = [
  { maxMinutes:   0, label:"On Time",  color:"#16A34A" },
  { maxMinutes:  30, label:"At Risk",  color:"#D97706" },
  { maxMinutes:  60, label:"Overdue",  color:"#DC2626" },
  { maxMinutes: 999, label:"Critical", color:"#991B1B" },
] as const;

export function getSlaStatus(minutesOverdue: number) {
  return SLA_BANDS.find(b => minutesOverdue <= b.maxMinutes) ?? SLA_BANDS[SLA_BANDS.length - 1];
}

export const STATUS_LABEL: Record<string, string> = {
  assigned:"Assigned", accepted:"Accepted", en_route:"En Route",
  arrived:"Arrived", in_progress:"In Progress", parts_required:"Parts Required",
  parts_sourced:"Parts Sourced", resumed:"Resumed", quality_check:"Quality Check",
  completed:"Completed", invoiced:"Invoiced", payment_pending:"Payment Pending",
  paid:"Paid", closed:"Closed", cancelled:"Cancelled",
};

export const STATUS_COLOR: Record<string, { bg:string; text:string; border:string }> = {
  assigned:       { bg:"#EFF6FF", text:"#1D4ED8", border:"#BFDBFE" },
  accepted:       { bg:"#F0FDF4", text:"#15803D", border:"#BBF7D0" },
  en_route:       { bg:"#FFF7ED", text:"#9A3412", border:"#FED7AA" },
  arrived:        { bg:"#F0F9FF", text:"#0369A1", border:"#BAE6FD" },
  in_progress:    { bg:"#FFF1F2", text:"#9F1239", border:"#FECDD3" },
  parts_required: { bg:"#FEFCE8", text:"#713F12", border:"#FEF08A" },
  parts_sourced:  { bg:"#F7FEE7", text:"#3F6212", border:"#D9F99D" },
  resumed:        { bg:"#F0FDFA", text:"#134E4A", border:"#99F6E4" },
  quality_check:  { bg:"#FDF4FF", text:"#701A75", border:"#F0ABFC" },
  completed:      { bg:"#ECFDF5", text:"#065F46", border:"#6EE7B7" },
  cancelled:      { bg:"#FEF2F2", text:"#991B1B", border:"#FECACA" },
  closed:         { bg:"#F8FAFC", text:"#1E293B", border:"#CBD5E1" },
};
