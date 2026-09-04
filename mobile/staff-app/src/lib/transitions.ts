/**
 * Real service_jobs status machine (home_service_assignment + execution
 * engines) -- app/engines/execution/constants.py is the source of truth.
 *
 * MODULE-L5-36: this used to model field_ops' status set (en_route/arrived/
 * in_progress/quality_check/closed), which belongs to a dead engine with
 * zero rows platform-wide. Each transition here maps to a DISTINCT jobsApi
 * action (accept/onTheWay/reachedSite/... /complete), not a single generic
 * "update status" call -- the real backend has no generic status-PUT
 * endpoint for this job family.
 */
export type JobAction =
  | "accept" | "reject" | "onTheWay" | "reachedSite" | "startInspection"
  | "completeInspection" | "startService" | "workDone" | "complete";

export const NEXT_ACTION: Record<string, JobAction[]> = {
  assigned:            ["accept", "reject"],
  accepted:            ["onTheWay"],
  on_the_way:          ["reachedSite"],
  reached_site:        ["startInspection"],
  inspection_started:  ["completeInspection"],
  inspection_done:     ["startService"],
  service_started:     ["workDone", "complete"],
  work_done:           ["complete"],
  quote_required:      ["complete"],
};

export const ACTION_LABEL: Record<JobAction, string> = {
  accept:"Accept Job", reject:"Reject Job", onTheWay:"On The Way",
  reachedSite:"Reached Site", startInspection:"Start Inspection",
  completeInspection:"Complete Inspection", startService:"Start Service",
  workDone:"Work Done", complete:"Complete & Submit",
};

export const ACTION_VARIANT: Record<JobAction, "primary"|"success"|"danger"|"secondary"> = {
  accept:"primary", reject:"danger", onTheWay:"primary", reachedSite:"primary",
  startInspection:"primary", completeInspection:"secondary", startService:"primary",
  workDone:"secondary", complete:"success",
};

export const STATUS_LABEL: Record<string, string> = {
  pending_assignment:"Pending Assignment", assigned:"Assigned", accepted:"Accepted",
  scheduled:"Scheduled", on_the_way:"On The Way", reached_site:"Reached Site",
  inspection_started:"Inspecting", inspection_done:"Inspection Done",
  quote_required:"Quote Required", service_started:"In Service", work_done:"Work Done",
  customer_not_available:"Customer Not Available", completed:"Completed",
  cancelled:"Cancelled", failed:"Failed",
};

export const STATUS_COLOR: Record<string, { bg:string; text:string; border:string }> = {
  pending_assignment: { bg:"#F8FAFC", text:"#1E293B", border:"#CBD5E1" },
  assigned:            { bg:"#E8F2F0", text:"#0F6B60", border:"#DFE9E7" },
  accepted:            { bg:"#F0FDF4", text:"#15803D", border:"#BBF7D0" },
  scheduled:           { bg:"#E8F2F0", text:"#0F6B60", border:"#DFE9E7" },
  on_the_way:          { bg:"#FFF7ED", text:"#9A3412", border:"#FED7AA" },
  reached_site:        { bg:"#E8F2F0", text:"#0F6B60", border:"#DFE9E7" },
  inspection_started:  { bg:"#FDF4FF", text:"#701A75", border:"#F0ABFC" },
  inspection_done:     { bg:"#FDF4FF", text:"#701A75", border:"#F0ABFC" },
  quote_required:      { bg:"#FEFCE8", text:"#713F12", border:"#FEF08A" },
  service_started:     { bg:"#FFF1F2", text:"#9F1239", border:"#FECDD3" },
  work_done:           { bg:"#F7FEE7", text:"#3F6212", border:"#D9F99D" },
  customer_not_available: { bg:"#FEF2F2", text:"#991B1B", border:"#FECACA" },
  completed:           { bg:"#ECFDF5", text:"#065F46", border:"#6EE7B7" },
  cancelled:           { bg:"#FEF2F2", text:"#991B1B", border:"#FECACA" },
  failed:              { bg:"#FEF2F2", text:"#991B1B", border:"#FECACA" },
};
