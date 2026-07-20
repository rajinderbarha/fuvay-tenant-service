import { z } from "zod";

/** Runtime validation of GET /v1/auth/sessions items — never displays a raw/unvalidated device identifier. */
export const sessionSummarySchema = z.object({
  session_id: z.string().min(1),
  device_name: z.string().max(200).nullable(),
  device_type: z.string().max(100).nullable(),
  ip_address: z.string().max(64).nullable(),
  last_active_at: z.string().datetime({ offset: true }).or(z.string().min(1)),
  is_current: z.boolean(),
  is_trusted: z.boolean(),
  is_approved: z.boolean(),
  created_at: z.string().datetime({ offset: true }).or(z.string().min(1)),
});

export type ValidatedSessionSummary = z.infer<typeof sessionSummarySchema>;

export function parseSessionList(items: unknown[]): { valid: ValidatedSessionSummary[]; droppedCount: number } {
  const valid: ValidatedSessionSummary[] = [];
  let droppedCount = 0;
  for (const item of items) {
    const result = sessionSummarySchema.safeParse(item);
    if (result.success) valid.push(result.data);
    else droppedCount += 1;
  }
  return { valid, droppedCount };
}
