import { z } from "zod";

export const warrantyClaimSchema = z.object({
  claim_id: z.string(),
  job_id: z.string(),
  claim_type: z.string(),
  description: z.string(),
  amount_requested: z.number(),
  amount_approved: z.number().nullable(),
  status: z.string(),
  provider_response_due_at: z.string().nullable(),
  provider_resolution: z.string().nullable(),
  warranty_days: z.number().nullable(),
  warranty_expires_at: z.string().nullable(),
  admin_attention_required: z.boolean(),
  customer_credit_id: z.string().nullable(),
  created_at: z.string(),
}).passthrough();

export const warrantyClaimListSchema = z.object({
  claims: z.array(warrantyClaimSchema),
  has_next: z.boolean(),
  next_cursor: z.string().nullable(),
});

export const refundRequestSchema = z.object({
  id: z.string(),
  complaint_id: z.string(),
  job_id: z.string().nullable(),
  booking_id: z.string().nullable(),
  status: z.string(),
  requested_amount: z.string().nullable(),
  approved_amount: z.string().nullable(),
  provider_response_due_at: z.string().nullable(),
  escalation_reason: z.string().nullable(),
  resolution_method: z.string().nullable(),
  customer_credit_id: z.string().nullable(),
  created_at: z.string().nullable(),
}).passthrough();

export const refundRequestListSchema = z.array(refundRequestSchema);

export type WarrantyClaim = z.infer<typeof warrantyClaimSchema>;
export type RefundRequest = z.infer<typeof refundRequestSchema>;
