import { z } from "zod";

/**
 * Mirrors app/engines/serviceability/models.py#CustomerAddress via the
 * generic ServiceOSBase.to_dict() (every column, UUIDs/datetimes
 * stringified) — see CUSTOMER-L5-07-contract-matrix.md. `latitude`/
 * `longitude` are Postgres `Numeric` columns; FastAPI/Pydantic serializes
 * them as JSON numbers, so they are coerced here rather than parsed as
 * strings.
 */
export const addressSchema = z.object({
  id: z.string().min(1),
  customer_id: z.string().min(1),
  tenant_id: z.string().nullable(),
  name: z.string().nullable(),
  phone: z.string().nullable(),
  address_line_1: z.string().min(1),
  address_line_2: z.string().nullable(),
  landmark: z.string().nullable(),
  city: z.string().min(1),
  district: z.string().nullable(),
  state: z.string().min(1),
  country: z.string().min(1),
  zipcode: z.string().min(1),
  latitude: z.number().nullable(),
  longitude: z.number().nullable(),
  is_default: z.boolean(),
  is_active: z.boolean(),
  created_at: z.string().nullable(),
  updated_at: z.string().nullable(),
});

export type ValidatedAddress = z.infer<typeof addressSchema>;

export function parseAddress(payload: unknown): ValidatedAddress | null {
  const result = addressSchema.safeParse(payload);
  return result.success ? result.data : null;
}

const addressListSchema = z.object({ addresses: z.array(z.unknown()), total: z.number().int().nonnegative() });

export interface AddressListResult {
  addresses: ValidatedAddress[];
  droppedCount: number;
}

/** Drops individually-invalid rows rather than failing the whole list — the same resilience pattern used throughout this app since CUSTOMER-L5-03. */
export function parseAddressList(payload: unknown): AddressListResult | null {
  const envelope = addressListSchema.safeParse(payload);
  if (!envelope.success) return null;

  const addresses: ValidatedAddress[] = [];
  let droppedCount = 0;
  for (const raw of envelope.data.addresses) {
    const parsed = parseAddress(raw);
    if (parsed) addresses.push(parsed);
    else droppedCount += 1;
  }
  return { addresses, droppedCount };
}

const deleteResponseSchema = z.object({ address_id: z.string().min(1), deleted: z.boolean() });
export function parseDeleteAddressResponse(payload: unknown): { addressId: string; deleted: boolean } | null {
  const result = deleteResponseSchema.safeParse(payload);
  return result.success ? { addressId: result.data.address_id, deleted: result.data.deleted } : null;
}
