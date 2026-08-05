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
  /** Page-based: the Finance page calls `listAudit(1, 50)`. */
  listAudit: <T = FinanceListEnvelope>(page = 1, pageSize = 50) =>
    apiFetch<T>(`/v1/admin/finance/audit-logs${_q({ page, pageSize })}`),

  // ── Deposits ────────────────────────────────────────────────────────────
  // NOTE: `page_size`/`payment_status` are the real FastAPI Query param
  // names (finance_hub/admin_router.py) -- camelCase equivalents are also
  // sent for backward compatibility with existing call sites, but unknown
  // extra query params are just silently ignored by FastAPI, so the
  // snake_case ones below are what actually take effect.
  listDeposits: <T = FinanceListEnvelope>(params?: ListParams) => apiFetch<T>(`/v1/admin/finance/deposits${_q({
    ...params, page_size: params?.pageSize ?? params?.page_size,
  })}`),
  getDepositsSummary: <T = FinRow>() => apiFetch<T>("/v1/admin/finance/deposits/summary"),
  getDepositDetail: <T = FinRow>(id: string) => apiFetch<T>(`/v1/admin/finance/deposits/${id}`),
  approveDeposit: <T = FinRow>(id: string, notes?: string) =>
    apiFetch<T>(`/v1/admin/finance/deposits/${id}/approve`, { method: "POST", body: JSON.stringify({ notes }) }),
  rejectDeposit: <T = FinRow>(id: string, reason: string) =>
    apiFetch<T>(`/v1/admin/finance/deposits/${id}/reject`, { method: "POST", body: JSON.stringify({ reason }) }),
  recordOfflineDeposit: <T = FinRow>(id: string, amount: number, reference?: string, notes?: string) =>
    apiFetch<T>(`/v1/admin/finance/deposits/${id}/record-offline`, {
      method: "POST", body: JSON.stringify({ amount, reference, notes }),
    }),
  refundDeposit: <T = FinRow>(id: string, amount: number, reason: string) =>
    apiFetch<T>(`/v1/admin/finance/deposits/${id}/refund`, { method: "POST", body: JSON.stringify({ amount, reason }) }),
  adjustDeposit: <T = FinRow>(id: string, amount: number, reason: string, category = "manual") =>
    apiFetch<T>(`/v1/admin/finance/deposits/${id}/adjust`, {
      method: "POST", body: JSON.stringify({ amount, reason, category }),
    }),

  // ── Top-ups ─────────────────────────────────────────────────────────────
  listTopups: <T = FinanceListEnvelope>(params?: ListParams) => apiFetch<T>(`/v1/admin/finance/topups${_q({
    ...params,
    payment_status: params?.paymentStatus ?? params?.payment_status,
    page_size: params?.pageSize ?? params?.page_size,
  })}`),
  getTopupDetail: <T = FinRow>(id: string) => apiFetch<T>(`/v1/admin/finance/topups/${id}`),
  retryTopupCredit: <T = FinRow>(id: string) =>
    apiFetch<T>(`/v1/admin/finance/topups/${id}/retry-credit`, { method: "POST" }),
  refundTopup: <T = FinRow>(id: string, amount: number, reason?: string) =>
    apiFetch<T>(`/v1/admin/finance/topups/${id}/refund`, { method: "POST", body: JSON.stringify({ amount, reason }) }),

  // ── Warranty claims ─────────────────────────────────────────────────────
  listWarrantyClaims: <T = FinanceListEnvelope>(params?: ListParams) =>
    apiFetch<T>(`/v1/admin/finance/warranty-claims${_q(params)}`),
  getWarrantyClaimsSummary: <T = FinRow>() => apiFetch<T>("/v1/admin/finance/warranty-claims/summary"),
  getWarrantyClaimDetail: <T = FinRow>(id: string) => apiFetch<T>(`/v1/admin/finance/warranty-claims/${id}`),

  // ── Invoices ────────────────────────────────────────────────────────────
  listInvoices: <T = FinanceListEnvelope>(params?: ListParams) => apiFetch<T>(`/v1/admin/finance/invoices${_q(params)}`),
  getInvoicesSummary: <T = FinRow>() => apiFetch<T>("/v1/admin/finance/summary"),
  getInvoiceDetail: <T = FinRow>(id: string) => apiFetch<T>(`/v1/admin/service-invoices/${id}`),

  // ── Credits (customer service credit) ───────────────────────────────────
  listCreditAccounts: <T = FinanceListEnvelope>(params?: ListParams) => apiFetch<T>(`/v1/admin/finance/credits${_q(params)}`),
  /** Filterable credit ledger -- the page filters by tenant or event type
   * rather than fetching a single credit by id. */
  listCreditLedger: <T = FinanceListEnvelope>(params?: ListParams) =>
    apiFetch<T>(`/v1/admin/finance/credits${_q(params)}`),

  // ── Refund requests ─────────────────────────────────────────────────────
  listRefunds: <T = FinanceListEnvelope>(params?: ListParams) => apiFetch<T>(`/v1/admin/refund-requests${_q(params)}`),
  getRefundsSummary: <T = FinRow>() => apiFetch<T>("/v1/admin/finance/summary"),
  getRefundDetail: <T = FinRow>(id: string) => apiFetch<T>(`/v1/admin/refund-requests/${id}`),
  approveRefund: <T = FinRow>(id: string, reason?: string) =>
    apiFetch<T>(`/v1/admin/refund-requests/${id}/approve`, {
      method: "POST", body: JSON.stringify({ reason: reason ?? "" }),
    }),
  rejectRefund: <T = FinRow>(id: string, reason: string) =>
    apiFetch<T>(`/v1/admin/refund-requests/${id}/reject`, {
      method: "POST", body: JSON.stringify({ reason }),
    }),
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  recordRefund: <T = FinRow>(id: string, payload: any) =>
    apiFetch<T>(`/v1/admin/refund-requests/${id}/record`, {
      method: "POST", body: JSON.stringify(payload),
    }),
  /** Provider-side verification of a refund the provider says they paid. */
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  verifyProviderRefund: <T = FinRow>(id: string, payload?: any) =>
    apiFetch<T>(`/v1/admin/refund-requests/${id}/record`, {
      method: "POST", body: JSON.stringify({ ...payload, verified_by_admin: true }),
    }),

  // ── Financial events / ledger ───────────────────────────────────────────
  listFinancialEvents: <T = FinanceListEnvelope>(params?: ListParams) =>
    apiFetch<T>(`/v1/admin/financial-events${_q(params)}`),
  getFinancialEventsSummary: <T = FinRow>() => apiFetch<T>("/v1/admin/finance/summary"),
  getFinancialEventDetail: <T = FinRow>(id: string) => apiFetch<T>(`/v1/admin/financial-events/${id}`),
  getLedgerEntryDetail: <T = FinRow>(walletId: string) =>
    apiFetch<T>(`/v1/admin/finance/wallets/${walletId}/ledger`),

  // ── Provider charges (commission records) ───────────────────────────────
  listProviderCharges: <T = FinanceListEnvelope>(params?: ListParams) =>
    apiFetch<T>(`/v1/admin/commission-records${_q(params)}`),
  getProviderChargeDetail: <T = FinRow>(id: string) => apiFetch<T>(`/v1/admin/commission-records/${id}`),

  // ── Direct (cash/UPI-to-provider) payments ──────────────────────────────
  listDirectPayments: <T = FinanceListEnvelope>(params?: ListParams) =>
    apiFetch<T>(`/v1/admin/home-services/finance/payments${_q(params)}`),
  getDirectPaymentsSummary: <T = FinRow>() => apiFetch<T>("/v1/admin/home-services/finance/payments/summary"),
  getDirectPaymentDetail: <T = FinRow>(id: string) => apiFetch<T>(`/v1/admin/home-services/finance/payments/${id}`),
  remindDirectPaymentCustomer: <T = FinRow>(id: string) =>
    apiFetch<T>(`/v1/admin/home-services/finance/payments/${id}/remind-customer`, { method: "POST" }),
  openDirectPaymentDispute: <T = FinRow>(id: string, description?: string) =>
    apiFetch<T>(`/v1/admin/home-services/finance/payments/${id}/open-dispute`, {
      method: "POST", body: JSON.stringify({ description }),
    }),

  // ── Platform charge configuration ───────────────────────────────────────
  // Per-service/job-type completion-charge credit amounts (ServicePricingRule
  // rows, via HomeServicesFinanceService.list_charge_config) -- NOT the same
  // thing as the vertical monetization policy (that sets the flat per-job
  // credit default; this overrides it per master-service/job-type). Fixed
  // 2026-08-05: these previously pointed at the monetization policy
  // endpoints, an entirely different shape, so the config table always
  // rendered empty and Save silently created garbage monetization drafts.
  listChargeConfig: <T = FinanceListEnvelope>(params?: ListParams) =>
    apiFetch<T>(`/v1/admin/home-services/finance/charge-config${_q({ ...params, page_size: params?.pageSize ?? params?.page_size })}`),
  updateChargeConfig: <T = FinRow>(ruleId: string, completedJobDeductionCredits: number) =>
    apiFetch<T>(`/v1/admin/home-services/finance/charge-config/${ruleId}`, {
      method: "POST", body: JSON.stringify({ completed_job_deduction_credits: completedJobDeductionCredits }),
    }),

  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  createAdjustment: <T = FinRow>(payload: any) =>
    apiFetch<T>("/v1/admin/finance/credits", {
      method: "POST", body: JSON.stringify(payload),
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
};

// ── Top-up Plan (starter credit package + activation security deposit) ─────
// Separate versioned policy (HomeServicesActivationFinancePolicy) from the
// provider/customer charge policy above -- this one sets what a tenant pays
// to BUY credits (top-up price + GST) and their activation security
// deposit, not what a completed job charges them.
export interface TopupPlan {
  id: string; vertical_id: string; version_number: number; status: string; is_current: boolean;
  deposit_required: boolean; deposit_calculation_mode: string; deposit_amount_per_technician: number;
  minimum_deposit: number; technician_count_policy: string;
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
