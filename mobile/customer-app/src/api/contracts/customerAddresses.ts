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
  /**
   * Sent as a STRING, not a number: these are NUMERIC columns, and the serializer
   * renders a Decimal as `"30.6861187"` to avoid float rounding.
   *
   * Real bug this fixes: the schema said `z.number()`, so the whole saved-address
   * screen failed to parse -- and only once addresses actually HAD coordinates, which
   * the Google Places lookup started doing. Every address had null here before, and
   * null satisfies a nullable number, so the mismatch sat dormant until real data
   * arrived.
   *
   * Coerced rather than kept as text because the app treats these as coordinates. A
   * value that is not a real number becomes null instead of NaN -- an unparseable
   * coordinate is "we do not know", never a point on the map.
   */
  latitude: z.coerce.number().nullable().catch(null),
  longitude: z.coerce.number().nullable().catch(null),
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
