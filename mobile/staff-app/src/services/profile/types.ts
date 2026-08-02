export interface ProfileIdentityDTO {
  user_id: string;
  full_name: string;
  photo_url: string | null;
  masked_mobile: string | null;
  email_verified: boolean;
  mobile_verified: boolean;
  status: string;
}

export interface ProfileEmploymentDTO {
  tenant_id: string;
  business_name: string | null;
  staff_type: string | null;
  designation: string | null;
  joined_at: string | null;
  assigned_service_count: number;
  staff_reference: string | null;
}

export interface ProfileMissingItemDTO {
  code: string;
  label: string;
  destination: string;
}

export interface ProfileReadinessDTO {
  profile_percentage: number;
  completed: number;
  required: number;
  verified_documents: number;
  required_documents: number;
  account_verified: boolean;
  missing: ProfileMissingItemDTO[];
}

export type DocumentStatus = "pending_review" | "verified" | "changes_requested" | "rejected";

export interface StaffDocumentDTO {
  id: string;
  document_type: string;
  media_id: string;
  status: DocumentStatus;
  expiry_date: string | null;
  reviewer_note: string | null;
  is_current: boolean;
  submitted_at: string | null;
  reviewed_at: string | null;
}

export interface ProfileSecurityDTO {
  mfa_enabled: boolean;
  active_session_count: number;
}

export interface ProfileDetailDTO {
  identity: ProfileIdentityDTO;
  employment: ProfileEmploymentDTO;
  readiness: ProfileReadinessDTO;
  documents: StaffDocumentDTO[];
  required_document_types: string[];
  security: ProfileSecurityDTO;
}

export interface NotificationPreferencesDTO {
  push_enabled: boolean;
  categories: {
    job_updates: boolean;
    schedule_updates: boolean;
    payment_updates: boolean;
    account_updates: boolean;
  };
}
