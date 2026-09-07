// ═══════════════════════════════════════════════════════════════════════════
// Top-up credit + technician seats.
//
// Backs the header credit pill and its refill popup. One `status` call serves
// both: the pill renders on every page, so three round trips per navigation
// to draw one number would be a bad trade, and the popup should open with the
// plans already in hand rather than spinning over a number just clicked.
// ═══════════════════════════════════════════════════════════════════════════
import { apiFetch } from "./api";

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
  plans: TopupPlan[];
  currency: string;
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

/** ₹ with Indian digit grouping, no trailing .00 on round amounts. */
export function inr(n: number): string {
  return `₹${n.toLocaleString("en-IN", {
    minimumFractionDigits: Number.isInteger(n) ? 0 : 2,
    maximumFractionDigits: 2,
  })}`;
}
