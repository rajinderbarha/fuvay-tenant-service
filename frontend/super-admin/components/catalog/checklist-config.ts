import type { ChecklistCompletionGate, ChecklistPurpose } from "../../lib/api";

export const CHECKLIST_PURPOSES: ChecklistPurpose[] = ["PRE_ARRIVAL", "INSPECTION", "PRE_WORK", "EXECUTION", "SAFETY", "COMPLETION", "HANDOVER"];
export const CHECKLIST_GATES: Record<ChecklistPurpose, ChecklistCompletionGate[]> = {
  PRE_ARRIVAL: ["NONE", "REQUIRE_BEFORE_WORK_START"],
  INSPECTION: ["NONE", "REQUIRE_BEFORE_INSPECTION_COMPLETE", "REQUIRE_BEFORE_ESTIMATE_SUBMISSION"],
  PRE_WORK: ["NONE", "REQUIRE_BEFORE_WORK_START"],
  EXECUTION: ["NONE", "REQUIRE_BEFORE_JOB_COMPLETION"],
  SAFETY: ["NONE", "REQUIRE_BEFORE_WORK_START", "REQUIRE_BEFORE_JOB_COMPLETION"],
  COMPLETION: ["NONE", "REQUIRE_BEFORE_JOB_COMPLETION", "REQUIRE_BEFORE_HANDOVER"],
  HANDOVER: ["NONE", "REQUIRE_BEFORE_HANDOVER"],
};
export const checklistLabel = (value: string) => value === "NONE" ? "No completion gate" : value.replace(/^REQUIRE_/, "").replaceAll("_", " ").toLowerCase();
