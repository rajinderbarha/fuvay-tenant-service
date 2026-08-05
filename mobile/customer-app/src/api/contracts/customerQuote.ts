/**
 * DTOs for the customer quote-approval endpoints (`/v1/customer/quotes/*`,
 * confirmed via direct read of `app/engines/quote_checklist/customer_router.py`
 * + `quote_service.py`'s `get_quote`/`_customer_dict` customer-view logic,
 * both of which strip `provider_internal_notes` and recompute totals from
 * only `is_customer_visible` items server-side -- this contract never
 * types those excluded fields, since the backend never sends them to a
 * customer caller).
 */
import { z } from "zod";

export const quoteItemDtoSchema = z.object({
  id: z.string(),
  item_type: z.string(),
  item_name: z.string(),
  item_description: z.string().nullable(),
  quantity: z.string(),
  unit_price: z.string(),
  line_total: z.string(),
});

export const customerQuoteDtoSchema = z.object({
  id: z.string(),
  quote_number: z.string(),
  job_id: z.string(),
  status: z.string(),
  quote_type: z.string(),
  currency: z.string(),
  labour_amount: z.string(),
  parts_amount: z.string(),
  service_amount: z.string(),
  discount_amount: z.string(),
  tax_amount: z.string(),
  total_amount: z.string(),
  customer_payable_amount: z.string(),
  customer_visible_notes: z.string().nullable(),
  rejection_reason: z.string().nullable(),
  expires_at: z.string().nullable(),
  approved_at: z.string().nullable(),
  rejected_at: z.string().nullable(),
  sent_to_customer_at: z.string().nullable(),
  version_number: z.number(),
  is_current: z.boolean(),
  created_at: z.string().nullable(),
  items: z.array(quoteItemDtoSchema).optional(),
}).passthrough();
export type CustomerQuoteDto = z.infer<typeof customerQuoteDtoSchema>;

export const customerQuoteListDtoSchema = z.array(customerQuoteDtoSchema);
