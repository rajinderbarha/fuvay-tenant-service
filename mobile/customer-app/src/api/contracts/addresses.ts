/**
 * Mounted route confirmed via OpenAPI: /v1/customers/me/addresses (list,
 * create), /v1/customers/me/addresses/{id} (get/update/delete),
 * /v1/customers/me/addresses/{id}/set-default. Router source (app/engines/
 * serviceability/router.py) not fully traced this phase -- field shape
 * below is a conservative superset; adapters must not assume every field
 * is present.
 */
import { z } from "zod";

export const addressDtoSchema = z.object({
  id: z.string(),
  label: z.string().nullable().optional(),
  line1: z.string(),
  line2: z.string().nullable().optional(),
  city: z.string().nullable().optional(),
  state: z.string().nullable().optional(),
  zipcode: z.string().nullable().optional(),
  latitude: z.number().nullable().optional(),
  longitude: z.number().nullable().optional(),
  is_default: z.boolean().optional(),
});
export type AddressDto = z.infer<typeof addressDtoSchema>;
