// ═══════════════════════════════════════════════════════════════════════════
// Top-up credit + technician seats.
//
// Backs the header credit pill and its refill popup. One `status` call serves
// both: the pill renders on every page, so three round trips per navigation
// to draw one number would be a bad trade, and the popup should open with the
// plans already in hand rather than spinning over a number just clicked.
// ═══════════════════════════════════════════════════════════════════════════
import { activationPaymentApi, apiFetch, API_BASE, getToken } from "./api";
import type { RazorpayResult } from "../hooks/useRazorpayCheckout";

export type CreditState = "healthy" | "low" | "blocked" | "arrears";

export interface TopupPlan {
  id: string;
  name: string;
  description: string | null;
  base_amount: number;
  gst_percent: number;
  gst_amount: number;
  /** What you pay at the gateway. */
  total_amount: number;
  /** What reaches the wallet — base only, GST is never spendable credit. */
  credited_amount: number;
  /** Technicians this plan lets you add; also jobs bookable per slot. */
  seats: number;
  currency: string;
  is_default: boolean;
  validity_days?: number;
  never_expires?: boolean;
  sort_order: number;
}

export interface TopupStatus {
  credit_balance: number;
  booking_floor: number;
  warning_threshold: number;
  below_floor: boolean;
  below_warning: boolean;
  in_arrears: boolean;
  /** Resolved server-side so every surface agrees on what "low" means. */
  state: CreditState;
  entitled_seats: number;
  used_seats: number;
  available_seats: number;
  seats_over_limit: boolean;
  /** True when an enabled, verified Admin Razorpay configuration is usable. */
  checkout_configured: boolean;
  plans: TopupPlan[];
  currency: string;
  health_blocked: boolean;
  credits_preserved_during_health_block: boolean;
  topup_allowed_during_health_block: boolean;
  health_block_notice: string | null;
}

export interface TopupPurchase {
  id: string;
  status: "created" | "captured" | "failed";
  gateway_order_id: string;
  gateway_payment_id: string | null;
  amount: number;
  credited_amount: number | null;
  tax_amount: number | null;
  seats_granted: number | null;
  currency: string;
  invoice_number: string | null;
  invoice_issued_at: string | null;
  invoice_available: boolean;
  plan: TopupPlan | null;
  captured_at: string | null;
  created_at: string | null;
}

export interface TopupPurchasePage {
  items: TopupPurchase[];
  total: number;
  page: number;
  page_size: number;
}

export interface TopupOrder {
  order_id: string;
  amount: number;
  amount_paise: number;
  currency: string;
  key: string;
  activation_payment_order_id: string;
  topup_plan: TopupPlan | null;
  seats_granted: number;
  credited_amount: number;
  tax_amount: number;
  reused?: boolean;
  already_confirmed?: boolean;
}

export const topupApi = {
  status: () => apiFetch<TopupStatus>("/v1/tenant/home-services/topup-plans/status"),

  orders: (params: { status?: string; page?: number; page_size?: number } = {}) => {
    const query = new URLSearchParams();
    if (params.status) query.set("status", params.status);
    query.set("page", String(params.page ?? 1));
    query.set("page_size", String(params.page_size ?? 25));
    return apiFetch<TopupPurchasePage>(`/v1/tenant/home-services/topup-plans/orders?${query}`);
  },

  /**
   * Create the gateway order. No amount is sent — the server prices it from
   * the live catalogue, so a tampered client cannot buy seats cheaply.
   */
  createOrder: (planId?: string) =>
    apiFetch<TopupOrder>(
      "/v1/tenant/home-services/activation/funding/order",
      { method: "POST", body: JSON.stringify({ plan_id: planId }) },
    ),
};

export async function downloadTopupInvoice(orderId: string, invoiceNumber?: string | null): Promise<void> {
  const response = await fetch(
    `${API_BASE}/v1/tenant/home-services/topup-plans/orders/${encodeURIComponent(orderId)}/invoice`,
    { headers: { Authorization: `Bearer ${getToken() ?? ""}` } },
  );
  if (!response.ok) throw new Error("Invoice download is temporarily unavailable.");
  const blob = await response.blob();
  const href = URL.createObjectURL(blob);
  const anchor = document.createElement("a");
  anchor.href = href;
  anchor.download = `${invoiceNumber || "topup-invoice"}.pdf`;
  anchor.click();
  URL.revokeObjectURL(href);
}

/** Recover the same order if Checkout succeeds but its callback fails. */
export async function completeTopupPayment(order: TopupOrder, checkout: () => Promise<RazorpayResult>): Promise<void> {
  if (order.already_confirmed) return;
  try {
    const payment = await checkout();
    await activationPaymentApi.confirmFunding(payment);
  } catch (error) {
    try {
      const result = await activationPaymentApi.reconcileFunding<{ status?: string; captured?: boolean }>(order.order_id);
      if (result.status === "captured" || result.captured === true) return;
    } catch {
      // Preserve the original failure. A later retry reconciles this order
      // before offering another payment; only the server can grant credit.
    }
    throw error;
  }
}

/** ₹ with Indian digit grouping, no trailing .00 on round amounts. */
export function inr(n: number): string {
  return `₹${n.toLocaleString("en-IN", {
    minimumFractionDigits: Number.isInteger(n) ? 0 : 2,
    maximumFractionDigits: 2,
  })}`;
}
