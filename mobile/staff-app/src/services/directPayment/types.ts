export interface DirectPaymentJobDTO {
  job_id: string;
  job_reference: string;
  workflow_status: string;
  is_terminal: boolean;
}

export interface ExpectedAmountDTO {
  expected_amount: string | null;
  expected_amount_source: string | null;
  unresolved_reason: string | null;
  currency: string;
  approved_estimate: { quote_id: string; version_number: number; total_amount: string; is_approved: boolean } | null;
  visit_fee: string;
  visit_fee_adjustment: string;
  requires_direct_payment_record: boolean;
}

export type DirectPaymentMethod = "onsite_cash" | "onsite_upi" | "onsite_card" | "onsite_bank_transfer" | "onsite_other";
export type ReconciliationStatus =
  | "not_declared" | "awaiting_provider" | "awaiting_customer" | "confirmed"
  | "mismatched" | "disputed" | "cancelled" | "reversed";

export interface ProviderRecordDTO {
  id: string;
  declared_amount: string;
  expected_amount: string | null;
  currency: string;
  method: string;
  method_label: string;
  provider_confirmation: { state: string; at: string | null };
  customer_confirmation: { state: string; at: string | null; action: string | null };
  status: ReconciliationStatus;
  status_label: string;
  dispute_complaint_id: string | null;
  reminder_count: number;
  last_reminder_at: string | null;
}

export interface DirectPaymentPrerequisitesDTO {
  completion_proof_submitted: boolean;
  customer_handover_status: string;
}

export interface ClosureReadinessDTO {
  can_submit_provider_record: boolean;
  can_finalize: boolean;
  blockers: string[];
}

export interface DirectPaymentDetailDTO {
  job: DirectPaymentJobDTO;
  amount: ExpectedAmountDTO;
  prerequisites: DirectPaymentPrerequisitesDTO;
  provider_record: ProviderRecordDTO | null;
  closure_readiness: ClosureReadinessDTO;
  allowed_methods: DirectPaymentMethod[];
  allowed_actions: string[];
}
