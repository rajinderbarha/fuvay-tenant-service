/**
 * Customer-visible job status labels and colors.
 * Simplified from the staff transitions — customers only read status, not change it.
 */
export const CUSTOMER_STATUS_LABEL: Record<string,string> = {
  pending_assignment:"Finding a Technician",
  assigned:          "Technician Assigned",
  accepted:          "Technician Confirmed",
  en_route:          "On the Way",
  arrived:           "Technician Arrived",
  in_progress:       "Work in Progress",
  parts_required:    "Parts Being Arranged",
  parts_sourced:     "Parts Ready",
  resumed:           "Work Resumed",
  quality_check:     "Final Check",
  completed:         "Work Completed",
  invoiced:          "Invoice Sent",
  payment_pending:   "Payment Pending",
  paid:              "Paid",
  closed:            "Closed",
  cancelled:         "Cancelled",
};

export const CUSTOMER_STATUS_COLOR: Record<string,{bg:string;text:string;border:string}> = {
  pending_assignment:{ bg:"#EFF6FF", text:"#1D4ED8", border:"#BFDBFE" },
  assigned:          { bg:"#F0FDF4", text:"#15803D", border:"#BBF7D0" },
  accepted:          { bg:"#F0FDF4", text:"#15803D", border:"#BBF7D0" },
  en_route:          { bg:"#FFF7ED", text:"#9A3412", border:"#FED7AA" },
  arrived:           { bg:"#F0F9FF", text:"#0369A1", border:"#BAE6FD" },
  in_progress:       { bg:"#FFF1F2", text:"#9F1239", border:"#FECDD3" },
  completed:         { bg:"#ECFDF5", text:"#065F46", border:"#6EE7B7" },
  cancelled:         { bg:"#FEF2F2", text:"#991B1B", border:"#FECACA" },
  closed:            { bg:"#F8FAFC", text:"#1E293B", border:"#CBD5E1" },
};

// UX-07 Round 4 Pass 2: dark-mode variant of the same status palette. The
// light set above uses very pale backgrounds with saturated text, which
// loses contrast on dark surfaces (e.g. #EFF6FF-on-navy reads as washed-out
// white). This mirrors each status's hue but inverted toward dark
// surfaces with light, saturated text so status remains readable and each
// still carries a distinct hue as its non-color-alone backup (paired with
// the text label, which is the actual backup signal).
export const CUSTOMER_STATUS_COLOR_DARK: Record<string,{bg:string;text:string;border:string}> = {
  pending_assignment:{ bg:"#12233F", text:"#93C5FD", border:"#1E3A5F" },
  assigned:          { bg:"#123420", text:"#86EFAC", border:"#1F5A38" },
  accepted:          { bg:"#123420", text:"#86EFAC", border:"#1F5A38" },
  en_route:          { bg:"#3A2510", text:"#FDBA74", border:"#5C3D1A" },
  arrived:           { bg:"#0C2A3A", text:"#7DD3FC", border:"#164E63" },
  in_progress:       { bg:"#3A1424", text:"#FDA4AF", border:"#5C1F35" },
  completed:         { bg:"#0F2E22", text:"#6EE7B7", border:"#1B4B37" },
  cancelled:         { bg:"#3A1414", text:"#FCA5A5", border:"#5C1F1F" },
  closed:            { bg:"#1C2740", text:"#CBD5E1", border:"#374761" },
};

export const ACTIVE_STATUSES = ["pending_assignment","assigned","accepted","en_route","arrived","in_progress","parts_required","parts_sourced","resumed","quality_check"] as const;
export const TRACKABLE_STATUSES = ["en_route","arrived","in_progress"] as const;

export function isActive(status:string)    { return ACTIVE_STATUSES.includes(status as typeof ACTIVE_STATUSES[number]); }
export function isTrackable(status:string) { return TRACKABLE_STATUSES.includes(status as typeof TRACKABLE_STATUSES[number]); }
export function needsReview(status:string) { return status === "completed" || status === "closed"; }
