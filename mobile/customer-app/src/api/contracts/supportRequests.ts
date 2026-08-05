/**
 * `GET/POST /v1/customer/complaints`, `GET .../{{id}}`,
 * `POST/GET .../{{id}}/messages`, `POST .../{{id}}/cancel` -- all confirmed
 * real in `app/engines/complaints/customer_router.py`. This engine IS the
 * customer app's real "support request" system (see domain/
 * supportRequests.ts for why).
 */
import { z } from "zod";

export const supportRequestDtoSchema = z.object({
  id: z.string(),
  complaint_number: z.string(),
  record_type: z.string(),
  record_id: z.string(),
  booking_id: z.string().nullable(),
  complaint_type: z.string(),
  status: z.string(),
  title: z.string().nullable(),
  description: z.string(),
  requested_resolution: z.string().nullable(),
  customer_visible_summary: z.string().nullable(),
  created_at: z.string().nullable(),
  updated_at: z.string().nullable(),
  resolved_at: z.string().nullable(),
  closed_at: z.string().nullable(),
}).passthrough();
export type SupportRequestDto = z.infer<typeof supportRequestDtoSchema>;

export const supportRequestListResponseSchema = z.array(supportRequestDtoSchema);

export const createSupportRequestBodySchema = z.object({
  record_type: z.string(),
  record_id: z.string(),
  complaint_type: z.string(),
  description: z.string(),
  title: z.string().optional(),
  requested_resolution: z.string().optional(),
});
export type CreateSupportRequestBody = z.infer<typeof createSupportRequestBodySchema>;

export const supportRequestMessageDtoSchema = z.object({
  id: z.string(),
  sender_type: z.string(),
  message_text: z.string(),
  created_at: z.string(),
});
export type SupportRequestMessageDto = z.infer<typeof supportRequestMessageDtoSchema>;

export const supportRequestMessageListResponseSchema = z.array(supportRequestMessageDtoSchema);
