import { z } from "zod";

/**
 * Matches app/schemas/base.py `ApiResponse`/`ok()` exactly:
 * `{ success: true, data, links?, meta: { request_id, ... } }`. Every
 * mounted ServiceOS endpoint returns this envelope on success.
 */
export const apiSuccessEnvelopeSchema = z.object({
  success: z.literal(true),
  data: z.unknown(),
  meta: z.object({ request_id: z.string() }).passthrough(),
}).passthrough();

export interface ParsedSuccess<T> {
  data: T;
  requestId: string;
}

/** Unwraps the envelope and hands back only `data` + the correlation ID
 * -- callers pass a DTO-specific zod schema to validate `data` itself
 * before ever touching it (contract-first, per Phase D/F conventions).
 *
 * Generic over the SCHEMA type `S` (not a bare output type `T` via
 * `z.ZodType<T>`) -- any schema using `.default()` (e.g. `idempotent:
 * z.boolean().optional().default(false)`) has a real Input/Output type
 * split (Input allows undefined, Output never does). Parameterizing on
 * `z.ZodType<T>` makes TS infer `T` against the Input side in some call
 * sites, so `dataSchema.parse(...)`'s actual (always-Output) return value
 * no longer matched the declared `ParsedSuccess<T>` return type -- every
 * caller of a `.default()`-using schema (confirmDraftResponseSchema was
 * the one that surfaced it) got a false-positive type error on code that
 * was runtime-correct. `z.infer<S>` always resolves to the Output type,
 * matching what `.parse()` actually returns. */
export function parseApiSuccess<S extends z.ZodTypeAny>(raw: unknown, dataSchema: S): ParsedSuccess<z.infer<S>> {
  const envelope = apiSuccessEnvelopeSchema.parse(raw);
  const data: z.infer<S> = dataSchema.parse(envelope.data);
  return { data, requestId: envelope.meta.request_id };
}
