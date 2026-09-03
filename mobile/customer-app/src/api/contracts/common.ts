import { z } from "zod";

/** Every Fuvay API response this app has observed wraps its payload in
 * `{ ok, data, request_id, ... }` via app/schemas/base.py's `ok()` helper. */
export const apiEnvelopeSchema = <T extends z.ZodTypeAny>(dataSchema: T) =>
  z.object({
    ok: z.boolean().optional(),
    data: dataSchema,
    request_id: z.string().optional(),
  });

/** UUID-shaped string -- used for backend identifiers before they are
 * branded into a domain ID type by an adapter. Never coerced to number. */
export const uuidStringSchema = z.string().min(1);

export const isoTimestampSchema = z.string().regex(/^\d{4}-\d{2}-\d{2}[T ]\d{2}:\d{2}:\d{2}/);
export const isoDateSchema = z.string().regex(/^\d{4}-\d{2}-\d{2}$/);
