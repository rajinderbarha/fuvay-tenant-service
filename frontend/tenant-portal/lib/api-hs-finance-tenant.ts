// ═══════════════════════════════════════════════════════════════════════════
// Tenant Home Services finance + direct payments + activation payment
//   /v1/tenant/home-services/finance/*
//   /v1/tenant/home-services/direct-payments/*
//
// Real bug fixed here: app/(tenant)/home-services/finance/page.tsx and
// .../direct-payments/page.tsx have always imported `homeServicesFinanceApi`,
// `homeServicesDirectPaymentsApi`, `activationPaymentApi` and a dozen types
// from lib/api -- none of which were ever implemented, so both pages could
// not compile and the tenant-portal production build failed.
//
// Paths matched against the live OpenAPI schema
// (app/engines/*/hs_finance_router.py, direct_payments_router.py).
// ═══════════════════════════════════════════════════════════════════════════
import { apiFetch } from "./api";

/** See the tradeoff note in api-tenant-support.ts: these are large,
 * backend-shaped analytics payloads whose exact shape the calling page
 * already asserts. Permissive here, checked there; the durable fix is
 * schema tests over real captured payloads. */
// eslint-disable-next-line @typescript-eslint/no-explicit-any
type FinPayload = any;

export type HsFinanceOverview = FinPayload;
export type HsFinanceTxnRow = FinPayload;
/** One composed row across the usage-credit, cash/tax, and adjustment ledgers. */
export interface HsFinanceTxnRowFull {
  row_id: string;
  ledger: string;
  ledger_label: string;
  /** The value the `type` filter matches on — NOT a field called `type`. */
  event_type: string | null;
  event_label: string | null;
  status: string | null;
  description: string | null;
  reference: string | null;
  related_job_id: string | null;
  related_transaction_ref: string | null;
  debit: string | null;
  credit: string | null;
  usage_credit_balance_after: string | null;
  receipt_available: boolean;
  reversible: boolean;
  occurred_at: string | null;
}

export interface HsFinanceTxnPage {
  items: HsFinanceTxnRowFull[];
  total: number;
  page: number;
  page_size: number;
  ledgers: { value: string; label: string }[];
  /** Facets for the `type` and `status` filters. */
  types: string[];
  statuses: string[];
  ledger_totals: Record<string, { rows: number; debit_total: string; credit_total: string }>;
  never_combined_note: string;
}
export type HsCreditPackage = FinPayload;
export type HsTopupOrder = FinPayload;
// HsRefundRequest and the deposit refund-request endpoints were removed with
// the security deposit itself (migrations 317/318). A top-up is spent down
// as commission rather than held and returned, so there is nothing to
// refund and no request workflow to model.

export type HsFinanceReadinessCheck = FinPayload;
export type HsLiabilityHold = FinPayload;
export type HsDpQueue = FinPayload;
export type HsDpDetail = FinPayload;
export type HsDpRecord = FinPayload;

const FIN = "/v1/tenant/home-services/finance";
const DP = "/v1/tenant/home-services/direct-payments";
const HS_SETUP = "/v1/tenant/home-services/setup";

function post(body?: unknown): RequestInit {
  return { method: "POST", body: JSON.stringify(body ?? {}) };
}

function query(params?: Record<string, string | number | boolean | undefined>): string {
  if (!params) return "";
  const entries = Object.entries(params).filter(([, v]) => v !== undefined && v !== "");
  if (entries.length === 0) return "";
  return `?${new URLSearchParams(Object.fromEntries(entries.map(([k, v]) => [k, String(v)])))}`;
}

/** GET /v1/tenant/home-services/finance/commission-rates -- the provider
 * commission actually charged on this tenant's completed jobs, resolved the
 * same way execution/usage_credit_deduction.py resolves it (the job's own
 * category rate, falling back to the vertical policy default). */
export interface HsCommissionCategoryRate {
  category_id: string;
  category_name: string;
  /** null when this category has no rate of its own and inherits the default. */
  category_rate_pct: string | null;
  effective_rate_pct: string | null;
  using_default: boolean;
}
export interface HsCommissionRates {
  is_live: boolean;
  provider_model: string | null;
  default_rate_pct: string | null;
  basis: string;
  charged_as: string;
  categories: HsCommissionCategoryRate[];
  /** Populated only when percentage commission is NOT the active model. */
  not_live_reason: string | null;
}

export const homeServicesFinanceApi = {
  getOverview: <T = HsFinanceOverview>() => apiFetch<T>(FIN),
  getCommissionRates: <T = HsCommissionRates>() => apiFetch<T>(`${FIN}/commission-rates`),
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  getTransactions: <T = HsFinanceTxnPage>(params?: Record<string, any>) =>
    apiFetch<T>(`${FIN}/transactions${query(params)}`),
  /** Returns a `{ packages: [...] }` envelope, not a bare array. */
  getCreditPackages: <T = HsCreditPackage>() => apiFetch<T>(`${FIN}/credit-packages`),

  // ── Top-ups ─────────────────────────────────────────────────────────────
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  listTopups: <T = HsTopupOrder>(params?: Record<string, any>) =>
    apiFetch<T>(`${FIN}/top-ups${query(params)}`),
  /** The buy dialog passes a credit QUANTITY; anything richer can be passed
   * as an object and is forwarded as-is. Response includes real Razorpay
   * order fields (gateway_order_id, amount_paise, key) -- this call only
   * creates the gateway order, it posts NO credit. */
  createTopup: <T = HsTopupOrder>(payload: number | Record<string, unknown>) =>
    apiFetch<T>(`${FIN}/top-ups`, post(typeof payload === "number" ? { quantity: payload } : payload)),
  /**
   * Real bug fixed here: this endpoint (`/top-ups/confirm`, real, HMAC-
   * signature-verified, instant -- see tenant_hs_finance_router.py) existed
   * on the backend but had no frontend caller at all. Without it, the buy-
   * credits flow could only ever create a gateway order and then tell the
   * tenant to wait -- there was no way for a payment to actually complete,
   * so real usage credit could never be posted without someone manually
   * calling the webhook. This is the SAME server-verified, no-admin-
   * approval pattern already used for activation payments.
   */
  confirmTopup: <T = HsTopupOrder>(payload: { gateway_order_id: string; gateway_payment_id: string; signature: string }) =>
    apiFetch<T>(`${FIN}/top-ups/confirm`, post(payload)),
  /** Real gap fixed here: dismissing the Razorpay popup had no way to tell
   * the backend the attempt was abandoned, so every cancelled checkout left
   * a permanently "initiated" (pending-looking) row in the tenant's own
   * top-up table. */
  cancelTopup: <T = HsTopupOrder>(topupId: string) =>
    apiFetch<T>(`${FIN}/top-ups/${topupId}/cancel`, post()),

  /** Top-up order detail + receipt. Had no caller, so a completed top-up's
   *  receipt was unreachable from the Transactions tab. */
  getTopup: <T = HsTopupOrder>(topupId: string) => apiFetch<T>(`${FIN}/top-ups/${topupId}`),

  /** Returns a signed/streamed statement; the caller handles the download. */
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  exportStatement: <T = FinPayload>(params?: Record<string, any>) =>
    apiFetch<T>(`${FIN}/export${query(params)}`),
};

export const homeServicesDirectPaymentsApi = {
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  list: <T = HsDpQueue>(params?: Record<string, any>) => apiFetch<T>(`${DP}${query(params)}`),
  get: <T = HsDpDetail>(paymentId: string) => apiFetch<T>(`${DP}/${paymentId}`),
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  export: <T = FinPayload>(params?: Record<string, any>) => apiFetch<T>(`${DP}/export${query(params)}`),
  remind: <T = FinPayload>(paymentId: string) =>
    apiFetch<T>(`${DP}/${paymentId}/remind-customer`, post()),
  openDispute: <T = FinPayload>(paymentId: string, reason: string) =>
    apiFetch<T>(`${DP}/${paymentId}/open-dispute`, post({ reason })),

  /**
   * Correct a declaration before the customer confirms it.
   *
   * The detail panel rendered an "Edit declaration" button gated on the
   * server's `available_actions.edit_declaration`, but the button had no
   * onClick at all -- so when the server said editing WAS allowed the control
   * enabled itself, looked actionable and did nothing. This endpoint existed
   * the whole time and had no caller.
   *
   * `expected_version` is the optimistic-concurrency guard: the server rejects
   * the write if the declaration moved on since it was read (e.g. the customer
   * confirmed in the meantime), so a correction can never silently overwrite a
   * newer state.
   */
  correctDeclaration: <T = FinPayload>(paymentId: string, body: {
    expected_version?: number;
    amount?: string;
    method?: string;
    reference_id?: string;
    note?: string;
    received_at?: string;
    correction_reason?: string;
    difference_reason?: string;
  }) => apiFetch<T>(`${DP}/${paymentId}/declaration`, { method: "PATCH", body: JSON.stringify(body) }),

  /** Expected payable, approved estimate and visit-fee treatment for a job
   *  BEFORE declaring. Never had a caller in any frontend, so nothing ever
   *  showed the provider what the canonical expected amount was. */
  declarationPreflight: <T = FinPayload>(jobId: string) =>
    apiFetch<T>(`/v1/tenant/home-services/jobs/${jobId}/direct-payment/preflight`),

  /** Record a direct payment from the web portal. Declarations could only be
   *  created from the staff MOBILE app (`/v1/staff/service-jobs/{id}/
   *  mobile-direct-payment/declare`); this tenant-side endpoint had no caller,
   *  so office staff working in the portal could not record a payment at all. */
  createDeclaration: <T = FinPayload>(jobId: string, body: {
    amount: string; method: string; reference_id?: string; note?: string;
    received_at?: string; difference_reason?: string;
  }) => apiFetch<T>(`/v1/tenant/home-services/jobs/${jobId}/direct-payment/declaration`, post(body)),
};

export const onboardingDeclarationsApi = {
  /**
   * Correction to an earlier note in this file: a real declarations resource
   * DOES exist. `/v1/tenant/home-services/setup/declarations` was written
   * but its router was never mounted, so it 404'd and looked absent. The
   * router is now mounted and these point at it.
   *
   * Acceptance is append-only and versioned server-side -- accepting v1 of a
   * policy says nothing about v2, which is what makes it auditable.
   */
  list: <T = FinPayload>() => apiFetch<T>(`${HS_SETUP}/declarations`),
  /** Append-only consent record: the keys the tenant just accepted. */
  accept: <T = FinPayload>(declarationKeys: string[]) =>
    apiFetch<T>(`${HS_SETUP}/declarations`, post({ declaration_keys: declarationKeys })),
};

/**
 * Correction to an earlier note in this file: dedicated activation-payment
 * endpoints DO exist. `/v1/tenant/home-services/activation/*` was written
 * but its router was never mounted, so every route 404'd and the capability
 * looked missing. These previously fell back to the generic finance top-up
 * with a purpose flag; they now call the real activation orders.
 */
export const activationPaymentApi = {
  getFundingQuote: <T = HsTopupOrder>() =>
    apiFetch<T>("/v1/tenant/home-services/activation/funding/quote"),
  createFundingOrder: <T = HsTopupOrder>() =>
    apiFetch<T>("/v1/tenant/home-services/activation/funding/order", post()),
  confirmFunding: <T = HsTopupOrder>(result: {
    razorpay_order_id: string; razorpay_payment_id: string; razorpay_signature: string;
  }) => apiFetch<T>("/v1/tenant/home-services/activation/funding/confirm", post(result)),
  reconcileFunding: <T = HsTopupOrder>(orderId: string) =>
    apiFetch<T>(`/v1/tenant/home-services/activation/funding/${encodeURIComponent(orderId)}/reconcile`, post()),
  createCreditPackageOrder: <T = HsTopupOrder>(packageId?: string, payload?: Record<string, unknown>) =>
    apiFetch<T>("/v1/tenant/home-services/activation/credit-package/order", post({ ...payload, package_id: packageId })),
};
