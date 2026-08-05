/**
 * Route confirmed mounted (GET/POST /customer/quotes/*, app/engines/
 * quote_checklist/customer_router.py) and role-guarded with
 * `require_customer`. Exact response field names for
 * ServiceJobQuoteService.get_quote/list_customer_quotes were not traced
 * this phase (service implementation not read) -- this schema is
 * deliberately conservative (only fields this app currently needs) and
 * additional unknown fields are ignored (zod's default passthrough-off
 * behavior on `.object` still allows extra keys through unless `.strict()`
 * is used, which is intentionally NOT applied here).
 */
import { z } from "zod";

export const quoteDtoSchema = z.object({
  id: z.string(),
  job_id: z.string(),
  status: z.string(),
  amount: z.union([z.number(), z.string()]).nullable(),
  currency: z.string().optional(),
  visit_fee: z.union([z.number(), z.string()]).nullable().optional(),
  notes: z.string().nullable().optional(),
  expires_at: z.string().nullable().optional(),
  created_at: z.string().nullable().optional(),
});
export type QuoteDto = z.infer<typeof quoteDtoSchema>;
