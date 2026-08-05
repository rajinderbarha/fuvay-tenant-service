/**
 * DTO for GET /v1/customer/global-services and POST /v1/customer/
 * global-services/leads (app/engines/global_services). Fields copied
 * directly from PlatformGlobalService.to_dict() / GlobalServiceLead
 * .to_dict() -- nothing guessed. This list is intentionally NOT
 * serviceability-checked: it is shown to every customer regardless of
 * ZIP/address/vertical, unlike bookable_categories on the Home
 * aggregation.
 */
import { z } from "zod";

export const globalServiceDtoSchema = z.object({
  id: z.string(),
  name: z.string(),
  tagline: z.string().nullable(),
  description: z.string().nullable(),
  icon_url: z.string().nullable(),
  display_order: z.number(),
  is_active: z.boolean(),
});

export const globalServicesListResponseSchema = z.array(globalServiceDtoSchema);

export const globalServiceLeadDtoSchema = z.object({
  id: z.string(),
  global_service_id: z.string(),
  status: z.string(),
});
