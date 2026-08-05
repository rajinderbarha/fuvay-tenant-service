/**
 * DTO for `GET/DELETE/POST .../set-default /v1/customers/me/addresses`
 * (`CustomerAddress.to_dict()` -- the generic column-introspection
 * `ServiceOSBase.to_dict()`, confirmed via direct read of
 * `app/models/base.py` + `app/engines/serviceability/models.py`).
 */
import { z } from "zod";

export const customerAddressDtoSchema = z.object({
  id: z.string(),
  customer_id: z.string(),
  tenant_id: z.string().nullable(),
  // Added migration 223 (Add/Edit Address phase) -- Home/Work/Other,
  // distinct from `name` (the recipient's full name).
  label: z.string().nullable(),
  name: z.string().nullable(),
  phone: z.string().nullable(),
  address_line_1: z.string(),
  address_line_2: z.string().nullable(),
  landmark: z.string().nullable(),
  city: z.string(),
  district: z.string().nullable(),
  state: z.string(),
  country: z.string(),
  zipcode: z.string(),
  latitude: z.number().nullable(),
  longitude: z.number().nullable(),
  is_default: z.boolean(),
  is_active: z.boolean(),
  created_at: z.string(),
  updated_at: z.string().nullable(),
}).passthrough();
export type CustomerAddressDto = z.infer<typeof customerAddressDtoSchema>;

export const addressListResponseSchema = z.object({
  addresses: z.array(customerAddressDtoSchema),
  total: z.number(),
});

export const deleteAddressResponseSchema = z.object({
  address_id: z.string(),
  deleted: z.boolean(),
});
