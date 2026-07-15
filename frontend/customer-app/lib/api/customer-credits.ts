/**
 * Customer Credits (wallet) API module.
 *
 * MODULE-L5-17: a customer earns service credits from dispute settlements/refunds
 * (customer_credits engine, /v1/me/credits), but the customer app had NO surface
 * — the customer could not see the balance it holds or where it came from. This
 * wires the read side (and the booking preview/apply helpers).
 *
 * Real router: app/engines/customer_credits/customer_router.py (prefix /v1/me/credits)
 *   GET  /              GET /summary        GET /{id}
 *   POST /preview-apply POST /apply
 */
import { apiFetch } from "./client";

export interface CreditSummary {
  total_credits: number;
  active_credits: number;
  used_credits: number;
  expired_credits: number;
  cancelled_credits: number;
  active_credit_balance: number;
  credits_from_disputes: number;
}

export interface Credit {
  id: string;
  credit_number: string;
  amount: string;
  remaining_amount: string;
  currency: string;
  credit_type: string;
  source: string;
  status: string;
  issued_reason?: string | null;
  customer_message?: string | null;
  valid_from?: string | null;
  expires_at?: string | null;
  created_at?: string | null;
}

export async function getCreditSummary(): Promise<CreditSummary> {
  return apiFetch<CreditSummary>("/v1/me/credits/summary");
}

export async function listMyCredits(status?: string): Promise<Credit[]> {
  const qs = status ? `?status=${encodeURIComponent(status)}` : "";
  const d = await apiFetch<{ credits: Credit[] }>(`/v1/me/credits${qs}`);
  return d.credits ?? [];
}

export async function getCredit(creditId: string): Promise<Credit> {
  return apiFetch<Credit>(`/v1/me/credits/${creditId}`);
}

export interface CreditApplyPreview {
  credit_applied: string;
  amount_after_credit: string;
  remaining_credit_balance: string;
  [k: string]: unknown;
}

export async function previewApplyCredit(
  bookingAmount: number, creditToApply: number,
): Promise<CreditApplyPreview> {
  return apiFetch<CreditApplyPreview>("/v1/me/credits/preview-apply", {
    method: "POST",
    body: JSON.stringify({ booking_amount: bookingAmount, credit_amount_to_apply: creditToApply }),
  });
}

export async function applyCreditToBooking(
  bookingId: string, creditToApply: number,
): Promise<unknown> {
  return apiFetch("/v1/me/credits/apply", {
    method: "POST",
    body: JSON.stringify({ booking_id: bookingId, credit_amount_to_apply: creditToApply }),
  });
}
