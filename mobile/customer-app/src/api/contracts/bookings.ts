/**
 * DTO shape verified against app/engines/final_records/models.py
 * `ServiceBooking.to_dict()` -- the canonical customer booking record.
 * Served by /v1/customer/bookings (list/detail) per home_service_
 * assignment/customer_router.py, whose `list_bookings` handler queries
 * this exact ServiceBooking table.
 */
import { z } from "zod";

export const serviceBookingDtoSchema = z.object({
  id: z.string(),
  booking_number: z.string(),
  draft_id: z.string(),
  customer_id: z.string().nullable(),
  tenant_id: z.string().nullable(),
  category_id: z.string(),
  offering_id: z.string(),
  job_type_id: z.string().nullable(),
  customer_name: z.string().nullable(),
  city: z.string().nullable(),
  zipcode: z.string().nullable(),
  preferred_date: z.string().nullable(),
  preferred_time_window: z.string().nullable(),
  price_snapshot: z.record(z.string(), z.unknown()).nullable(),
  provider_snapshot: z.object({
    provider_name: z.string().nullable().optional(),
    rating: z.number().nullable().optional(),
    public_badges: z.array(z.string()).optional(),
  }).nullable().optional(),
  status: z.string(),
  assignment_status: z.string(),
  failure_reason: z.string().nullable(),
  created_at: z.string().nullable(),
  updated_at: z.string().nullable(),
});
export type ServiceBookingDto = z.infer<typeof serviceBookingDtoSchema>;
