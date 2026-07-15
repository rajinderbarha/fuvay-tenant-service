/**
 * Customer Invoices API module.
 *
 * MODULE-L5-18: the invoice_payment customer router (/v1/customer/service-invoices)
 * had detail / payment-status / confirm-payment / receipt but no LIST, and the
 * customer app had no invoice surface at all — the customer could not see its
 * invoices, confirm it paid the provider, or get a receipt. This wires it (a
 * customer list endpoint was added to the canonical invoice_payment engine).
 *
 * Real router: app/engines/invoice_payment/customer_router.py
 *   GET  /v1/customer/service-invoices
 *   GET  /v1/customer/service-invoices/{id}
 *   GET  /v1/customer/service-invoices/{id}/payment-status
 *   POST /v1/customer/service-invoices/{id}/confirm-payment
 *   GET  /v1/customer/service-invoices/{id}/receipt
 */
import { apiFetch } from "./client";

export interface InvoiceItem {
  id: string;
  description?: string | null;
  quantity?: number | string | null;
  unit_price?: number | string | null;
  line_total?: number | string | null;
}

export interface Invoice {
  id: string;
  invoice_number: string;
  booking_id: string;
  job_id: string;
  status: string;
  currency: string;
  subtotal_amount: string;
  discount_amount: string;
  tax_amount: string;
  total_amount: string;
  platform_fee_amount: string;
  customer_payable_amount: string;
  credit_applied_amount?: string;
  payment_mode: string;
  payment_status: string;
  issued_at?: string | null;
  paid_at?: string | null;
  items?: InvoiceItem[];
  receipt_type?: string;
  generated_at?: string | null;
}

export interface PaymentStatusEntry {
  payment_mode: string;
  payment_status: string;
  collected_amount: string;
  customer_confirmed: boolean;
  created_at: string;
}

export async function listMyInvoices(status?: string): Promise<Invoice[]> {
  const qs = status ? `?status=${encodeURIComponent(status)}` : "";
  const d = await apiFetch<{ invoices: Invoice[] }>(`/v1/customer/service-invoices${qs}`);
  return d.invoices ?? [];
}

export async function getInvoice(invoiceId: string): Promise<Invoice> {
  return apiFetch<Invoice>(`/v1/customer/service-invoices/${invoiceId}`);
}

export async function getPaymentStatus(invoiceId: string): Promise<PaymentStatusEntry[]> {
  const d = await apiFetch<PaymentStatusEntry[]>(
    `/v1/customer/service-invoices/${invoiceId}/payment-status`);
  return Array.isArray(d) ? d : [];
}

export async function confirmPayment(invoiceId: string): Promise<{ confirmed: boolean }> {
  return apiFetch<{ confirmed: boolean }>(
    `/v1/customer/service-invoices/${invoiceId}/confirm-payment`, { method: "POST", body: "{}" });
}

export interface ApplyCreditResult {
  invoice_id: string;
  original_payable: number;
  credit_applied: number;
  new_payable: number;
  remaining_credit_balance: number;
}

// MODULE-L5-28: apply the customer's service credit to reduce what they owe.
export async function applyCreditToInvoice(
  invoiceId: string, creditAmount: number,
): Promise<ApplyCreditResult> {
  return apiFetch<ApplyCreditResult>(
    `/v1/customer/service-invoices/${invoiceId}/apply-credit`,
    { method: "POST", body: JSON.stringify({ credit_amount_to_apply: creditAmount }) });
}

export async function getReceipt(invoiceId: string): Promise<Invoice> {
  return apiFetch<Invoice>(`/v1/customer/service-invoices/${invoiceId}/receipt`);
}
