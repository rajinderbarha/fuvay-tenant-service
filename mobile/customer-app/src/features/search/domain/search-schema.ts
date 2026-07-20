import { z } from "zod";
import { categorySummarySchema } from "../../home/domain/category-schema";
import { offeringSummarySchema } from "../../category/domain/offering-schema";

/**
 * Mirrors GET /v1/customer/search — app/engines/customer_flow/service.py#search
 * (CUSTOMER-L5-04-contract-matrix.md). Categories are hard-capped at 5 by
 * the backend regardless of `page`/`page_size` (`.limit(5)`, no `.offset()`),
 * and offerings use `.limit(page_size)` with **no `.offset()` at all** — the
 * `page` query param is accepted but never actually used to paginate. This
 * schema therefore backs a single-shot search, not an infinite list — see
 * search-queries.ts.
 */
export const searchResponseSchema = z.object({
  query: z.string(),
  categories: z.array(z.unknown()),
  offerings: z.array(z.unknown()),
});

export interface SearchResults {
  query: string;
  categories: z.infer<typeof categorySummarySchema>[];
  offerings: z.infer<typeof offeringSummarySchema>[];
  droppedCount: number;
}

export function parseSearchResponse(payload: unknown): SearchResults | null {
  const envelope = searchResponseSchema.safeParse(payload);
  if (!envelope.success) return null;

  const categories: z.infer<typeof categorySummarySchema>[] = [];
  const offerings: z.infer<typeof offeringSummarySchema>[] = [];
  let droppedCount = 0;

  for (const raw of envelope.data.categories) {
    const result = categorySummarySchema.safeParse(raw);
    if (result.success) categories.push(result.data);
    else droppedCount += 1;
  }
  for (const raw of envelope.data.offerings) {
    const result = offeringSummarySchema.safeParse(raw);
    if (result.success) offerings.push(result.data);
    else droppedCount += 1;
  }

  return { query: envelope.data.query, categories, offerings, droppedCount };
}
