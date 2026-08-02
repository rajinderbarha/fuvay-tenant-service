/** DTOs matching app/engines/execution/mobile_estimate_service.py verbatim. */

export interface EstimateJobDTO {
  job_id: string;
  job_reference: string;
  workflow_status: string;
  is_terminal: boolean;
}

export interface InspectionSourceDTO {
  completed: boolean;
  instance_id?: string;
  diagnosis_summary: string | null;
  evidence_count: number;
}

export type QuoteItemType = "labour" | "part" | "material" | "service" | "visit_charge" | "discount" | "tax" | "other";

export interface QuoteLineItemDTO {
  id: string;
  item_type: QuoteItemType;
  item_name: string;
  item_description: string | null;
  quantity: string;
  unit_price: string;
  line_total: string;
  is_customer_visible: boolean;
}

export type QuoteStatus =
  | "draft" | "submitted_to_provider" | "provider_approved" | "provider_rejected"
  | "sent_to_customer" | "customer_approved" | "customer_rejected"
  | "revision_requested" | "revised" | "expired" | "cancelled";

export interface QuoteDTO {
  quote_id: string;
  version_number: number;
  is_current: boolean;
  status: QuoteStatus;
  quote_type: string;
  line_items: QuoteLineItemDTO[];
  valid_until: string | null;
  customer_notes: string | null;
}

export interface CalculationDTO {
  currency: string;
  labour_total: string;
  parts_total: string;
  subtotal: string;
  visit_fee_adjustment: string;
  tax_total: string;
  grand_total: string;
}

export interface VisitFeePolicyDTO {
  amount: number | null;
  currency: string;
  disposition: "not_tracked" | "unavailable";
}

export interface EstimateReadinessDTO {
  can_save: boolean;
  can_submit: boolean;
  blockers: string[];
}

export interface EstimateDetailDTO {
  job: EstimateJobDTO;
  inspection_source: InspectionSourceDTO;
  quote: QuoteDTO | null;
  calculation: CalculationDTO;
  visit_fee_policy: VisitFeePolicyDTO;
  readiness: EstimateReadinessDTO;
  next_approval_target: "customer";
  allowed_actions: string[];
  server_timestamp: string | null;
}
