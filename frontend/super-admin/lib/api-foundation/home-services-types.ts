/**
 * FRONTEND-CONNECT-01 — Consolidated Home Services types (super-admin).
 *
 * Re-exports what already exists in ../api.ts (source of truth, thousands of
 * lines, used by many pages — not forked) and adds the small number of types
 * the spec asks for with no existing equivalent. Payment architecture is
 * confirmed direct customer-to-provider payment + platform usage-credit
 * billing — NOT wallet/payout. Do not introduce wallet/payout types here.
 */
export type {
  MatchingDiagnosticsCandidate as ProviderMatch,
  MatchingDiagnosticsResult as MatchingDiagnostic,
  UsageCreditLedgerEntryAdmin as UsageCreditLedgerEntry,
} from "../api";

export type PaymentMode = "customer_pays_provider_directly";

export type CustomerPriceOptions = {
  low: number;
  mid: number;
  high: number;
  currency: "INR" | string;
  platform_fee_percent?: number;
};

export interface ServiceGroup { id: string; name: string; vertical?: string; }
export interface Service { id: string; name: string; service_group_id?: string; }
export interface ServiceType { id: string; name: string; service_id?: string; }
export interface Brand { id: string; name: string; }
export interface Issue { id: string; name: string; severity?: string; }
export interface ServiceOption { id: string; name: string; group?: string; }
export interface PricingRule { id: string; name: string; status?: string; }
export interface TenantService { id: string; tenant_id: string; offering_name?: string; }
export interface TenantServiceCoverage { tenant_id: string; offering_id: string; covered: boolean; }
export interface ServiceArea { id: string; tenant_id: string; name?: string; }
export interface AvailabilityRule { id: string; tenant_id: string; day_of_week?: number; }
export interface BookabilityStatus { is_bookable: boolean; is_visible?: boolean; }
export type JobStatus = string;
export interface Job { id: string; status: JobStatus; customer_id?: string; provider_id?: string; created_at?: string; }
export interface Technician { id: string; name?: string; status?: string; }
export interface CompletionProof { job_id: string; photos?: string[]; notes?: string; }
export interface UsageCreditBalance { tenant_id: string; balance: number; }
export interface AuditEvent { action_type?: string; actor_role?: string; request_id?: string; created_at?: string; }
