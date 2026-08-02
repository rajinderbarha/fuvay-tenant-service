export interface EmploymentBusinessDTO {
  tenant_id: string;
  name: string | null;
  logo_url: string | null;
  vertical_code: string | null;
  vertical_label: string | null;
}

export interface EmploymentReportsToDTO {
  display_name: string | null;
  designation: string | null;
}

export interface EmploymentInfoDTO {
  staff_id: string;
  staff_reference: string;
  staff_type: string | null;
  designation: string | null;
  status: string;
  status_known: boolean;
  joined_at: string | null;
  reports_to: EmploymentReportsToDTO | null;
}

export interface AssignmentItemDTO {
  id: string;
  code: string | null;
  name: string;
}

export type SkillVerificationStatus = "verified" | "pending";

export interface SkillDTO {
  id: string;
  name: string;
  verification_status: SkillVerificationStatus;
  verified_at: string | null;
  expires_at: string | null;
}

export interface EmploymentAssignmentsDTO {
  service_groups: AssignmentItemDTO[];
  job_types: AssignmentItemDTO[];
  verified_skills: SkillDTO[];
}

export interface EmploymentScopeDTO {
  service_area_summary: string | null;
  working_schedule_summary: string | null;
  effective_capability_count: number;
}

export interface PermissionGroupDTO {
  key: string;
  label: string;
  items: string[];
}

export interface PermissionsSummaryDTO {
  capability_count: number;
  groups: PermissionGroupDTO[];
}

export interface EmploymentDetailDTO {
  business: EmploymentBusinessDTO;
  employment: EmploymentInfoDTO | null;
  status_known: boolean;
  assignments: EmploymentAssignmentsDTO;
  scope: EmploymentScopeDTO | null;
  permissions: PermissionsSummaryDTO | null;
  allowed_actions: { request_correction: boolean };
}

export type CorrectionFieldKey =
  | "designation" | "reports_to" | "service_group" | "job_type"
  | "skill" | "service_area" | "joined_at";

export type CorrectionStatus = "pending_review" | "approved" | "changes_requested" | "rejected" | "applied";

export interface CorrectionRequestDTO {
  id: string;
  field_key: CorrectionFieldKey;
  current_value: string | null;
  requested_value: string;
  reason: string;
  status: CorrectionStatus;
  reviewer_note: string | null;
  reviewed_at: string | null;
  applied_at: string | null;
  created_at: string;
  auto_applies: boolean;
}
