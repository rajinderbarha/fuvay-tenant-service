// ═══════════════════════════════════════════════════════════════════════════
// Home Services Finance workspace (admin)
//
// Real bug fixed here: app/admin/home-services/finance/page.tsx has always
// imported `homeServicesFinanceApi` and
// `homeServicesFinanceMonetizationApi`, but neither was ever implemented --
// so the whole Finance workspace could not compile and the super-admin
// production build failed. The monetization ENGINE was additionally never
// mounted (every route 404'd) until this session.
//
// Every path below is matched against a real route in the live OpenAPI
// schema. Finance surfaces are deliberately spread across several existing
// admin routers (finance hub, refund-requests, service-invoices,
// commission-records, provider-wallets) -- this client is the single
// façade the Finance page talks to, so the page never has to know which
// engine owns which slice.
// ═══════════════════════════════════════════════════════════════════════════
import { apiFetch } from "./api";

/** These admin finance surfaces return large, backend-shaped analytics
 * payloads that differ per tab. Rather than this client guessing at
 * hundreds of field names (which would drift from the backend the moment
 * anything changed), every method is GENERIC with a permissive default:
 * the calling page declares the exact shape it needs -- and several
 * already do, e.g. `OverviewData` in the Finance page. That keeps the
 * shape assertion next to the code that actually depends on it. */
/**
 * TRADEOFF, deliberately made and worth revisiting:
 *
 * These admin surfaces return large, backend-shaped analytics payloads that
 * differ per tab. The calling pages ALREADY declare and assert their own
 * shapes (e.g. `OverviewData` in the Finance page, `Row` in the directory
 * workspaces) -- so the shape contract lives next to the code that depends
 * on it, which is the right place for it.
 *
 * A permissive default here restores exactly the contract those pages were
 * written against. It does NOT give compile-time checking of these
 * payloads -- and this session proved that matters: a `public_badges`
 * shape mismatch in the CUSTOMER app silently broke Booking Review because
 * a schema said `string[]` where the backend sent objects.
 *
 * The durable fix for these admin surfaces is the same one used there:
 * validate real captured payloads against real schemas in a test. That is
 * follow-up work, not something to fake with hand-guessed field lists.
 */
// eslint-disable-next-line @typescript-eslint/no-explicit-any
type AdminPayload = any;

type FinRow = AdminPayload;

function _q(params?: Record<string, string | number | boolean | undefined>): string {
  if (!params) return "";
  const entries = Object.entries(params).filter(([, v]) => v !== undefined && v !== "");
  if (entries.length === 0) return "";
  return `?${new URLSearchParams(Object.fromEntries(entries.map(([k, v]) => [k, String(v)])))}`;
}

/** Superset of the filters these finance list routes accept. `pageSize` is
 * the page's own paging vocabulary (used for bulk CSV export); it is passed
 * through to the query string as-is. */
/** An open filter bag: these finance list routes accept many per-tab
 * filters and the page owns which ones are meaningful for each tab.
 * Enumerating them here would just drift from the backend. */
type ListParams = {
  limit?: number; offset?: number; page?: number; pageSize?: number;
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  [key: string]: any;
};

/** Every list route returns an `{ items, total }` envelope. */
export interface FinanceListEnvelope<T = Record<string, unknown>> {
  items: T[];
  total?: number;
  pagination?: { page?: number; page_size?: number; total?: number };
}

export const homeServicesFinanceApi = {
  // ── Overview ────────────────────────────────────────────────────────────
  getOverview: <T = FinRow>() => apiFetch<T>("/v1/admin/home-services/finance/overview"),
  getLedgerHealth: <T = FinRow>() => apiFetch<T>("/v1/admin/home-services/finance/ledger-health"),
  runReconciliation: <T = FinRow>() => apiFetch<T>("/v1/admin/finance/home-services/reconcile", { method: "POST" }),
  /** Page-based: the Finance page calls `listAudit(1, 50)`. */
  listAudit: <T = FinanceListEnvelope>(page = 1, pageSize = 50) =>
    apiFetch<T>(`/v1/admin/finance/home-services/audit${_q({ page, page_size: pageSize })}`),

  // The Deposits and Deposit-refund-request sections were removed with the
  // security deposit itself (migrations 317/318). Providers hold spendable
  // credit and purchased seats; there is no held balance to administer and
  // nothing to refund.

  // ── Direct payments (customer pays the provider directly) ───────────────
  // Read-only operational evidence. Customer/provider actions deliberately
  // stay in their own apps; the platform admin may only list and inspect.
  // Note the params
  // here are the admin router's own (`q`, `pageSize`, `confirmed`), which do
  // NOT match the tenant queue's (`search`, `limit`, `method`).
  getDirectPaymentsSummary: <T = FinRow>() =>
    apiFetch<T>("/v1/admin/home-services/finance/payments/summary"),
  listDirectPayments: <T = FinanceListEnvelope>(params?: {
    status?: string; tenant_id?: string; confirmed?: boolean; q?: string;
    date_from?: string; date_to?: string; page?: number; pageSize?: number;
  }) => apiFetch<T>(`/v1/admin/home-services/finance/payments${_q(params)}`),
  getDirectPayment: <T = FinRow>(paymentId: string) =>
    apiFetch<T>(`/v1/admin/home-services/finance/payments/${paymentId}`),
  // ── Top-ups ─────────────────────────────────────────────────────────────
  listTopups: <T = FinanceListEnvelope>(params?: ListParams) => apiFetch<T>(`/v1/admin/finance/home-services/topups${_q({
    ...params,
    payment_status: params?.paymentStatus ?? params?.payment_status,
    date_from: params?.dateFrom ?? params?.date_from,
    date_to: params?.dateTo ?? params?.date_to,
    page_size: params?.pageSize ?? params?.page_size,
  })}`),
  getTopupDetail: <T = FinRow>(id: string) => apiFetch<T>(`/v1/admin/finance/home-services/topups/${id}`),
  retryTopupCredit: <T = FinRow>(id: string) =>
    apiFetch<T>(`/v1/admin/finance/topups/${id}/retry-credit`, { method: "POST" }),
  refundTopup: <T = FinRow>(id: string, amount: number, reason?: string) =>
    apiFetch<T>(`/v1/admin/finance/topups/${id}/refund`, { method: "POST", body: JSON.stringify({ amount, reason }) }),

  // ── Warranty claims ─────────────────────────────────────────────────────
  listWarrantyClaims: <T = FinanceListEnvelope>(params?: ListParams) =>
    apiFetch<T>(`/v1/admin/finance/home-services/warranty-claims${_q({ ...params, page_size: params?.pageSize ?? params?.page_size })}`),
  getWarrantyClaimsSummary: <T = FinRow>() => apiFetch<T>("/v1/admin/finance/home-services/warranty-claims/summary"),
  getWarrantyClaimDetail: <T = FinRow>(id: string) => apiFetch<T>(`/v1/admin/finance/home-services/warranty-claims/${id}`),
  assignWarrantyReviewer: <T = FinRow>(id: string, reviewerId: string) =>
    apiFetch<T>(`/v1/admin/finance/warranty-claims/${id}/assign`, {
      method: "POST", body: JSON.stringify({ reviewer_id: reviewerId }),
    }),
  requestWarrantyDocuments: <T = FinRow>(id: string, notes: string) =>
    apiFetch<T>(`/v1/admin/finance/warranty-claims/${id}/request-documents`, {
      method: "POST", body: JSON.stringify({ notes }),
    }),
  approveWarrantyClaim: <T = FinRow>(id: string, amountApproved: number, adminNotes?: string) =>
    apiFetch<T>(`/v1/admin/finance/warranty-claims/${id}/approve`, {
      method: "POST", body: JSON.stringify({ amount_approved: amountApproved, admin_notes: adminNotes }),
    }),
  rejectWarrantyClaim: <T = FinRow>(id: string, rejectionReason: string, adminNotes?: string) =>
    apiFetch<T>(`/v1/admin/finance/warranty-claims/${id}/reject`, {
      method: "POST", body: JSON.stringify({ rejection_reason: rejectionReason, admin_notes: adminNotes }),
    }),
  settleWarrantyClaim: <T = FinRow>(id: string) =>
    apiFetch<T>(`/v1/admin/finance/warranty-claims/${id}/settle`, { method: "POST" }),

  // ── Invoices ────────────────────────────────────────────────────────────
  listInvoices: <T = FinanceListEnvelope>(params?: ListParams) => apiFetch<T>(`/v1/admin/finance/home-services/invoices${_q({ ...params, page_size: params?.pageSize ?? params?.page_size })}`),
  getInvoicesSummary: <T = FinRow>() => apiFetch<T>("/v1/admin/finance/home-services/invoices/summary"),
  getInvoiceDetail: <T = FinRow>(id: string) => apiFetch<T>(`/v1/admin/finance/home-services/invoices/${id}`),
  getCreditsSummary: <T = FinRow>() => apiFetch<T>("/v1/admin/finance/home-services/credits/summary"),

  // ── Credits (customer service credit) ───────────────────────────────────
  listCreditAccounts: <T = FinanceListEnvelope>(params?: ListParams) =>
    apiFetch<T>(`/v1/admin/finance/home-services/credit-accounts${_q({
      ...params,
      lowBalanceOnly: params?.lowBalanceOnly ?? params?.low_balance_only,
      page_size: params?.pageSize ?? params?.page_size,
    })}`),
  /** Filterable credit ledger -- the page filters by tenant or event type
   * rather than fetching a single credit by id. */
  listCreditLedger: <T = FinanceListEnvelope>(params?: ListParams) =>
    apiFetch<T>(`/v1/admin/finance/home-services/credit-ledger${_q({
      ...params,
      tenant_id: params?.tenantId ?? params?.tenant_id,
      job_id: params?.jobId ?? params?.job_id,
      event_type: params?.eventType ?? params?.event_type,
      date_from: params?.dateFrom ?? params?.date_from,
      date_to: params?.dateTo ?? params?.date_to,
      page_size: params?.pageSize ?? params?.page_size,
    })}`),

  // ── Refund requests ─────────────────────────────────────────────────────
  listRefunds: <T = FinanceListEnvelope>(params?: ListParams) => apiFetch<T>(`/v1/admin/finance/home-services/refunds${_q({ ...params, page_size: params?.pageSize ?? params?.page_size })}`),
  getRefundsSummary: <T = FinRow>() => apiFetch<T>("/v1/admin/finance/home-services/refunds/summary"),
  getRefundDetail: <T = FinRow>(id: string) => apiFetch<T>(`/v1/admin/finance/home-services/refunds/${id}`),
  issueRefundCreditRemedy: <T = FinRow>(id: string, amount: number, reason: string) =>
    apiFetch<T>(`/v1/admin/refund-requests/${id}/credit-remedy`, {
      method: "POST", body: JSON.stringify({ amount, reason }),
    }),
  approveRefund: <T = FinRow>(id: string, approvedAmount?: number) =>
    apiFetch<T>(`/v1/admin/refund-requests/${id}/approve`, {
      method: "POST", body: JSON.stringify({ approved_amount: approvedAmount }),
    }),
  rejectRefund: <T = FinRow>(id: string, reason: string) =>
    apiFetch<T>(`/v1/admin/refund-requests/${id}/reject`, {
      method: "POST", body: JSON.stringify({ reason }),
    }),
  recordRefund: <T = FinRow>(id: string, amount: number, proofMediaUrl?: string) =>
    apiFetch<T>(`/v1/admin/refund-requests/${id}/record`, {
      method: "POST", body: JSON.stringify({ recorded_amount: amount, proof_media_url: proofMediaUrl || null }),
    }),
  /** Provider-side verification of a refund the provider says they paid. */
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  verifyProviderRefund: <T = FinRow>(id: string, payload?: any) =>
    apiFetch<T>(`/v1/admin/refund-requests/${id}/verify`, { method: "POST", body: JSON.stringify(payload ?? {}) }),

  // ── Financial events / ledger ───────────────────────────────────────────
  listFinancialEvents: <T = FinanceListEnvelope>(params?: ListParams) =>
    apiFetch<T>(`/v1/admin/finance/home-services/financial-events${_q({ ...params, page_size: params?.pageSize ?? params?.page_size })}`),
  getFinancialEventsSummary: <T = FinRow>() => apiFetch<T>("/v1/admin/finance/home-services/financial-events/summary"),
  getFinancialEventDetail: <T = FinRow>(id: string) => apiFetch<T>(`/v1/admin/finance/home-services/financial-events/${id}`),
  getLedgerEntryDetail: <T = FinRow>(entryId: string) =>
    apiFetch<T>(`/v1/admin/finance/home-services/credit-ledger/${entryId}`),

  // ── Provider charges (commission records) ───────────────────────────────
  listProviderCharges: <T = FinanceListEnvelope>(params?: ListParams) =>
    apiFetch<T>(`/v1/admin/finance/home-services/provider-charges${_q({ ...params, q: params?.q, charge_model: params?.chargeModel ?? params?.charge_model, page_size: params?.pageSize ?? params?.page_size })}`),
  getProviderChargeDetail: <T = FinRow>(id: string) => apiFetch<T>(`/v1/admin/finance/home-services/provider-charges/${id}`),

  createAdjustment: <T = FinRow>(payload: {
    tenantId: string; direction: "credit" | "debit"; creditUnits: string | number;
    reasonCode: string; detailedReason: string; supportingReference?: string;
  }) =>
    apiFetch<T>("/v1/admin/finance/home-services/adjustments", {
      method: "POST", body: JSON.stringify({
        tenant_id: payload.tenantId,
        direction: payload.direction,
        credit_units: payload.creditUnits,
        reason_code: payload.reasonCode,
        detailed_reason: payload.detailedReason,
        supporting_reference: payload.supportingReference,
      }),
    }),
};

// ── Home Services monetization policy (its own engine) ─────────────────────

export const homeServicesFinanceMonetizationApi = {
  getCurrent: <T = FinRow>() => apiFetch<T>("/v1/admin/home-services/finance/monetization/current"),
  getDraft: <T = FinRow>() => apiFetch<T>("/v1/admin/home-services/finance/monetization/draft"),
  getHistory: <T = FinRow>() => apiFetch<T>("/v1/admin/home-services/finance/monetization/history"),
  saveDraft: <T = FinRow>(payload: Record<string, unknown>) =>
    apiFetch<T>("/v1/admin/home-services/finance/monetization/draft", {
      method: "POST", body: JSON.stringify(payload),
    }),
  validate: (payload: Record<string, unknown>) =>
    apiFetch<{ valid: boolean; errors: string[]; warnings?: string[] }>(
      "/v1/admin/home-services/finance/monetization/validate",
      { method: "POST", body: JSON.stringify(payload) },
    ),
  /** `example_service_amount` is a STRING -- the backend parses it as
   * Decimal, and a JS float would lose precision on money. */
  preview: <T = FinRow>(payload: Record<string, unknown>, exampleServiceAmount = "500") =>
    apiFetch<T>("/v1/admin/home-services/finance/monetization/preview", {
      method: "POST",
      body: JSON.stringify({ draft: payload, example_service_amount: exampleServiceAmount }),
    }),
  publish: <T = FinRow>(reason: string) =>
    apiFetch<T>("/v1/admin/home-services/finance/monetization/publish", {
      method: "POST", body: JSON.stringify({ reason }),
    }),
  discardDraft: <T = FinRow>() =>
    apiFetch<T>("/v1/admin/home-services/finance/monetization/draft", { method: "DELETE" }),
  listJobTypeRules: <T = { items: MonetizationJobTypeRule[] }>(policyId: string) =>
    apiFetch<T>(`/v1/admin/home-services/finance/monetization/policies/${policyId}/job-type-rules`),
  upsertJobTypeRule: <T = MonetizationJobTypeRule>(policyId: string, jobTypeId: string, payload: Partial<MonetizationJobTypeRule>) =>
    apiFetch<T>(`/v1/admin/home-services/finance/monetization/policies/${policyId}/job-type-rules/${jobTypeId}`, {
      method: "PUT", body: JSON.stringify(payload),
    }),
};

export interface MonetizationJobTypeRule {
  id?: string;
  policy_id?: string;
  job_type_id: string;
  customer_charge_enabled: boolean;
  customer_charge_basis?: "booking_price_snapshot";
  provider_charge_enabled: boolean;
  provider_charge_model: "INHERIT" | "FIXED_CREDITS";
  provider_charge_credit_units: string | null;
  provider_chargeable_event: "job_completed" | "consultation_completed";
  status: "active" | "inactive";
}

// ── Activation finance policy (starter credit + credit thresholds) ─────────
// Separate versioned policy (HomeServicesActivationFinancePolicy) from the
// provider/customer charge policy above -- this one sets what a tenant pays
// to BUY credits (top-up price + GST) and the credit thresholds that replaced
// the security deposit, not what a completed job charges them.
export interface TopupPlan {
  id: string; vertical_id: string; version_number: number; status: string; is_current: boolean;
  credit_warning_threshold: number; credit_booking_floor: number; seat_accrual_mode: string;
  initial_credit_purchase_required: boolean; credit_package_base_amount: number;
  credit_package_gst_percent: number; credited_wallet_amount: number;
  completion_deduction_policy: string | null; currency: string;
  effective_from: string | null; effective_until: string | null; change_summary: string | null;
  published_at: string | null; created_at: string; updated_at: string;
}

export const homeServicesTopupPlanApi = {
  getCurrent: <T = TopupPlan>() => apiFetch<T>("/v1/admin/home-services/finance/monetization/topup-plan/current"),
  getDraft: <T = TopupPlan>() => apiFetch<T>("/v1/admin/home-services/finance/monetization/topup-plan/draft"),
  getHistory: <T = { items: TopupPlan[] }>() => apiFetch<T>("/v1/admin/home-services/finance/monetization/topup-plan/history"),
  saveDraft: <T = TopupPlan>(payload: Partial<TopupPlan>) =>
    apiFetch<T>("/v1/admin/home-services/finance/monetization/topup-plan/draft", {
      method: "POST", body: JSON.stringify(payload),
    }),
  validate: (payload: Partial<TopupPlan>) =>
    apiFetch<{ errors: string[]; warnings?: string[] }>(
      "/v1/admin/home-services/finance/monetization/topup-plan/validate",
      { method: "POST", body: JSON.stringify(payload) },
    ),
  publish: <T = TopupPlan>(reason: string) =>
    apiFetch<T>("/v1/admin/home-services/finance/monetization/topup-plan/publish", {
      method: "POST", body: JSON.stringify({ reason }),
    }),
  discardDraft: <T = TopupPlan>() =>
    apiFetch<T>("/v1/admin/home-services/finance/monetization/topup-plan/draft", { method: "DELETE" }),
};
