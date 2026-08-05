/**
 * DTOs for `/v1/customer/service-jobs/{jobId}/parts-requests` and
 * `/v1/customer/service-jobs/parts-requests/{id}/approve|decline`
 * (confirmed via direct read of `app/engines/execution/customer_parts_router.py`
 * + `home_service_service.py`'s `_customer_safe_parts_request`).
 */
import { z } from "zod";

export const partsRequestItemDtoSchema = z.object({
  parts_request_id: z.string(),
  status: z.string(),
  part_name: z.string(),
  quantity: z.number(),
  unit_amount: z.string(),
  line_total: z.string(),
  reason: z.string(),
  customer_approval_required: z.boolean(),
  submitted_at: z.string().nullable(),
  decided_at: z.string().nullable(),
  rejection_reason: z.string().nullable(),
});
export type PartsRequestItemDto = z.infer<typeof partsRequestItemDtoSchema>;

export const partsRequestListDtoSchema = z.object({
  currency: z.string(),
  previous_estimated_total: z.string(),
  additional_total: z.string(),
  new_estimated_total: z.string(),
  items: z.array(partsRequestItemDtoSchema),
});
export type PartsRequestListDto = z.infer<typeof partsRequestListDtoSchema>;
