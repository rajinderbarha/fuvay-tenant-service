/**
 * FRONTEND-CONNECT-01 — Consolidated Home Services types (tenant-portal).
 *
 * Re-exports the types that already exist in ../api.ts (do not fork them —
 * that file is the source of truth and is used by hundreds of call sites)
 * and adds the small number of types the spec asks for that had no existing
 * equivalent. Payment architecture is confirmed direct customer-to-provider
 * payment + platform usage-credit billing — NOT wallet/payout. Do not add
 * wallet/payout types here even though a legacy /provider/wallet page exists
 * elsewhere in the repo (out of scope for this sprint to rename).
 */
export type {
  ProviderStatusResult,
  OfferingBookableStatus as BookabilityStatus,
  EnabledOffering as TenantService,
  TenantCreditWalletDetail as UsageCreditBalance,
  ProviderServiceArea as ServiceArea,
  ProviderTeamMember as Technician,
  ProviderAvailabilityRule as AvailabilityRule,
} from "../api";

// ── Types with no existing equivalent in lib/api.ts ──────────────────────────

/** Confirmed architecture: direct customer-to-provider payment, not a wallet/payout model. */
export type PaymentMode = "customer_pays_provider_directly";

export type CustomerPriceOptions = {
  low: number;
  mid: number;
  high: number;
  currency: "INR" | string;
  platform_fee_percent?: number;
};

export interface ServiceGroup {
  id: string;
  name: string;
  vertical?: string;
}

export interface Service {
  id: string;
  name: string;
  service_group_id?: string;
}

export interface ServiceType {
  id: string;
  name: string;
  service_id?: string;
}

export interface Brand {
  id: string;
  name: string;
}

export interface Issue {
  id: string;
  name: string;
  severity?: string;
}

export interface ServiceOption {
  id: string;
  name: string;
  group?: string;
}

export interface PricingRule {
  id: string;
  name: string;
  status?: string;
}

export interface TenantServiceCoverage {
  tenant_id: string;
  offering_id: string;
  covered: boolean;
}

export interface MatchingDiagnostic {
  job_id?: string;
  candidates_evaluated?: number;
  selected_provider_id?: string | null;
}

export interface ProviderMatch {
  provider_id: string;
  score?: number;
  distance_km?: number;
}

export type JobStatus = string; // full enum lives in components/shared/ui.tsx JOB_STATUS_MAP_TP

export interface Job {
  id: string;
  status: JobStatus;
  customer_id?: string;
  provider_id?: string;
  created_at?: string;
}

export interface CompletionProof {
  job_id: string;
  photos?: string[];
  notes?: string;
}

export interface UsageCreditLedgerEntry {
  id: string;
  tenant_id: string;
  amount: number;
  reason?: string;
  created_at?: string;
}

export interface AuditEvent {
  action_type?: string;
  actor_role?: string;
  request_id?: string;
  created_at?: string;
}
