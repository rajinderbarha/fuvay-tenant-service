import { z } from "zod";

/**
 * Mirrors the real, customer-facing `quote_checklist` engine
 * (`app/engines/quote_checklist/`, Sprint 22 backend, CUSTOMER-L5-14
 * customer client) — see CUSTOMER-L5-14-contract-matrix.md.
 *
 * Two deliberate, structural exclusions, both real disclosed backend
 * gaps (baseline-verification.md #5.3):
 * 1. `provider_internal_notes`/`created_by_user_id`/
 *    `created_by_staff_member_id`/`idempotency_key`/`locked_at` are never
 *    listed in `quoteSchema` at all — `z.object()`'s default
 *    unknown-key-stripping removes them, the same pattern used since
 *    CUSTOMER-L5-08.
 * 2. `GET /customer/quotes/{quote_id}` returns every line item
 *    regardless of `is_customer_visible` — `parseQuoteDetail` filters
 *    those out client-side after validation, since the server does not.
 */
export const quoteItemSchema = z.object({
  id: z.string().min(1),
  item_type: z.string().min(1),
  item_name: z.string().min(1),
  item_description: z.string().nullable().optional(),
  quantity: z.union([z.string(), z.number()]),
  unit_price: z.union([z.string(), z.number()]),
  line_total: z.union([z.string(), z.number()]),
  is_customer_visible: z.boolean(),
});
export type ValidatedQuoteItem = z.infer<typeof quoteItemSchema>;

export const quoteSchema = z.object({
  id: z.string().min(1),
  quote_number: z.string().min(1),
  job_id: z.string().min(1),
  status: z.string().min(1),
  quote_type: z.string().min(1),
  currency: z.string().min(1),
  labour_amount: z.union([z.string(), z.number()]),
  parts_amount: z.union([z.string(), z.number()]),
  service_amount: z.union([z.string(), z.number()]),
  discount_amount: z.union([z.string(), z.number()]),
  tax_amount: z.union([z.string(), z.number()]),
  total_amount: z.union([z.string(), z.number()]),
  customer_payable_amount: z.union([z.string(), z.number()]),
  customer_visible_notes: z.string().nullable().optional(),
  rejection_reason: z.string().nullable().optional(),
  revision_reason: z.string().nullable().optional(),
  created_at: z.string().nullable().optional(),
});
export type ValidatedQuote = z.infer<typeof quoteSchema>;

export interface ValidatedQuoteDetail extends ValidatedQuote {
  items: ValidatedQuoteItem[];
}

export function parseQuoteList(payload: unknown): ValidatedQuote[] | null {
  const parsed = z.array(z.unknown()).safeParse(payload);
  if (!parsed.success) return null;
  const quotes: ValidatedQuote[] = [];
  for (const raw of parsed.data) {
    const item = quoteSchema.safeParse(raw);
    if (item.success) quotes.push(item.data);
  }
  return quotes;
}

const quoteDetailResponseSchema = quoteSchema.extend({
  items: z.array(z.unknown()),
});

/** Drops individually-invalid items and any item not flagged `is_customer_visible` — resilient, never fails the whole screen for one bad row. */
export function parseQuoteDetail(payload: unknown): ValidatedQuoteDetail | null {
  const envelope = quoteDetailResponseSchema.safeParse(payload);
  if (!envelope.success) return null;

  const items: ValidatedQuoteItem[] = [];
  for (const raw of envelope.data.items) {
    const parsed = quoteItemSchema.safeParse(raw);
    if (parsed.success && parsed.data.is_customer_visible) items.push(parsed.data);
  }
  const { items: _rawItems, ...quote } = envelope.data;
  return { ...quote, items };
}

export function toNumber(value: string | number): number {
  return typeof value === "number" ? value : parseFloat(value);
}
