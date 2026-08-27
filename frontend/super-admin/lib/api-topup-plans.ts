// ═══════════════════════════════════════════════════════════════════════════
// Home Services top-up plans (/v1/admin/home-services/topup-plans)
//
// Matches app/engines/vertical_catalog/topup_plan_catalog_router.py. A plan is
// what a provider buys to operate: it grants wallet credit AND the technician
// seats that decide how many jobs they can run in one slot. It replaced the
// security deposit entirely.
// ═══════════════════════════════════════════════════════════════════════════
import { apiFetch } from "./api";

export interface TopupPlan {
  id: string;
  vertical_id: string;
  name: string;
  description: string | null;
  /** Pre-tax price. Also exactly what reaches the wallet. */
  base_amount: number;
  gst_percent: number;
  gst_amount: number;
  /** What the provider pays at the gateway (base + GST). */
  total_amount: number;
  /** What lands in the wallet — base only; GST is never spendable credit. */
  credited_amount: number;
  /** Technician seats granted. One seat = one technician = one more job per slot. */
  seats: number;
  currency: string;
  is_active: boolean;
  is_default: boolean;
  sort_order: number;
  /** How long the seats and credit stay live. 0 = the purchase never lapses. */
  validity_days: number;
  never_expires: boolean;
  created_at: string | null;
  updated_at: string | null;
}

export interface TopupPlanInput {
  name: string;
  base_amount: number;
  seats: number;
  gst_percent?: number;
  description?: string | null;
  is_active?: boolean;
  is_default?: boolean;
  sort_order?: number;
  /** 0 = never lapses, which is how every plan behaved before validity existed. */
  validity_days?: number;
}

const BASE = "/v1/admin/home-services/topup-plans";

export const topupPlanApi = {
  list: (activeOnly = false) =>
    apiFetch<{ plans: TopupPlan[]; total: number }>(
      `${BASE}${activeOnly ? "?active_only=true" : ""}`,
    ),

  get: (id: string) => apiFetch<TopupPlan>(`${BASE}/${id}`),

  create: (body: TopupPlanInput) =>
    apiFetch<TopupPlan>(BASE, { method: "POST", body: JSON.stringify(body) }),

  update: (id: string, patch: Partial<TopupPlanInput>) =>
    apiFetch<TopupPlan>(`${BASE}/${id}`, { method: "PATCH", body: JSON.stringify(patch) }),

  /** Only succeeds for a plan no payment order references — otherwise the
   *  API returns TOPUP_PLAN_IN_USE and it should be retired instead. */
  remove: (id: string) =>
    apiFetch<{ deleted: boolean; id: string }>(`${BASE}/${id}`, { method: "DELETE" }),
};
