/**
 * DTO shape verified directly against app/engines/final_records/models.py
 * `ServiceJob.to_dict()` -- this IS the exact JSON shape the canonical
 * customer-facing GET /v1/customer/service-jobs/{job_id}/tracking and
 * /v1/customer/jobs/{job_id} endpoints serialize from (both routers read
 * the same ServiceJob row; response envelope shape around it was not
 * independently re-verified per route this phase).
 */
import { z } from "zod";

export const serviceJobDtoSchema = z.object({
  id: z.string(),
  job_number: z.string(),
  booking_id: z.string(),
  customer_id: z.string().nullable(),
  tenant_id: z.string().nullable(),
  category_id: z.string(),
  offering_id: z.string(),
  job_type_id: z.string().nullable(),
  assigned_staff_id: z.string().nullable(),
  scheduled_date: z.string().nullable(),
  scheduled_time_window: z.string().nullable(),
  city: z.string().nullable(),
  zipcode: z.string().nullable(),
  status: z.string(),
  assignment_status: z.string(),
  failure_reason: z.string().nullable(),
  created_at: z.string().nullable(),
  updated_at: z.string().nullable(),
});
export type ServiceJobDto = z.infer<typeof serviceJobDtoSchema>;
