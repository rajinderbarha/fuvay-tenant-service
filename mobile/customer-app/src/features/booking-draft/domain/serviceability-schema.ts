import { z } from "zod";

/**
 * Mirrors app/engines/home_service_booking/serviceability_service.py#check's
 * literal return dict, plus the `draft_status` the router's
 * `check_serviceability` appends — see CUSTOMER-L5-07-contract-matrix.md.
 * This is the real, ID-space-correct check used by the booking-draft flow
 * — not the general `/v1/serviceability/*` engine, which is keyed to an
 * unrelated catalog and is never called by this app.
 */
export const serviceabilityResultSchema = z.object({
  serviceable: z.boolean(),
  available_provider_count: z.number().int().nonnegative(),
  matched_by: z.enum(["zipcode", "city"]).nullable(),
  message: z.string(),
  reason_code: z.string().nullable(),
  draft_status: z.string().min(1),
});

export type ValidatedServiceabilityResult = z.infer<typeof serviceabilityResultSchema>;

export function parseServiceabilityResult(payload: unknown): ValidatedServiceabilityResult | null {
  const result = serviceabilityResultSchema.safeParse(payload);
  return result.success ? result.data : null;
}
