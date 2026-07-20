import { z } from "zod";

/**
 * Mirrors app/engines/customer_flow/service.py#_customer_offering_summary —
 * the shared shape returned by both the category offering list and (with
 * extra fields) the offering detail endpoint. See
 * CUSTOMER-L5-04-contract-matrix.md.
 *
 * Deliberately NOT included here even though the backend response carries
 * them: `is_available` is hardcoded to `True` for every offering in
 * `_customer_offering_summary` (service.py line ~549) — it is not derived
 * from real provider/serviceability data, so treating it as a genuine
 * availability signal would be exactly the kind of fabricated availability
 * this sprint must not produce. It is parsed (so an unexpected `false` is
 * not silently dropped by the schema) but never rendered as a trustworthy
 * badge — see CUSTOMER-L5-04-known-gaps.md.
 */
export const offeringSummarySchema = z.object({
  id: z.string().min(1),
  name: z.string().min(1).max(200),
  slug: z.string().min(1).max(200),
  description: z.string().max(2000).nullable(),
  offering_class: z.string().min(1),
  customer_flow_type: z.string().min(1),
  primary_engine_key: z.string().nullable(),
  pricing_model: z.string().min(1),
  starting_price: z.number().nonnegative(),
  visit_fee: z.number().nonnegative(),
  appointment_fee: z.number().nonnegative(),
  requires_type: z.boolean(),
  requires_brand: z.boolean(),
  requires_address: z.boolean(),
  requires_slot: z.boolean(),
  requires_photo_upload: z.boolean(),
  is_available: z.boolean(),
  display_order: z.number().int(),
});

export type ValidatedOfferingSummary = z.infer<typeof offeringSummarySchema>;

const requiredFieldsSchema = z.object({
  requires_type: z.boolean(),
  requires_brand: z.boolean(),
  requires_address: z.boolean(),
  requires_slot: z.boolean(),
  requires_photo_upload: z.boolean(),
  requires_customer_notes: z.boolean(),
});

/** GET /v1/customer/categories/{category_slug}/offerings/{offering_slug} */
export const offeringDetailSchema = offeringSummarySchema.extend({
  category: z.object({ id: z.string().min(1), name: z.string().min(1), slug: z.string().min(1) }),
  required_fields: requiredFieldsSchema,
});

export type ValidatedOfferingDetail = z.infer<typeof offeringDetailSchema>;

export interface OfferingListPage {
  category: { id: string; name: string; slug: string; customer_flow_type: string };
  items: ValidatedOfferingSummary[];
  total: number;
  page: number;
  page_size: number;
  droppedCount: number;
}

const offeringListEnvelopeSchema = z.object({
  category: z.object({ id: z.string().min(1), name: z.string().min(1), slug: z.string().min(1), customer_flow_type: z.string().min(1) }),
  items: z.array(z.unknown()),
  total: z.number().int().nonnegative(),
  page: z.number().int().positive(),
  page_size: z.number().int().positive(),
});

/** Drops individually-invalid offering rows rather than failing the whole page — CUSTOMER-L5-03's same resilience pattern. */
export function parseOfferingListPage(payload: unknown): OfferingListPage | null {
  const envelope = offeringListEnvelopeSchema.safeParse(payload);
  if (!envelope.success) return null;

  const items: ValidatedOfferingSummary[] = [];
  let droppedCount = 0;
  for (const raw of envelope.data.items) {
    const result = offeringSummarySchema.safeParse(raw);
    if (result.success) items.push(result.data);
    else droppedCount += 1;
  }

  return { ...envelope.data, items, droppedCount };
}

export function parseOfferingDetail(payload: unknown): ValidatedOfferingDetail | null {
  const result = offeringDetailSchema.safeParse(payload);
  return result.success ? result.data : null;
}
