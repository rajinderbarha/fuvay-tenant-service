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
