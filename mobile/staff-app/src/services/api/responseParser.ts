import { ApiSuccessEnvelope, ProblemDetailBody } from "./types";

/**
 * Parses the two real backend envelope shapes (Phase F spec section 4;
 * confirmed against app/schemas/base.py). Never assumes a shape -- a
 * response that matches neither is treated as UNKNOWN_API_ERROR upstream
 * in errorMapper, not force-cast.
 */
export function isSuccessEnvelope<T>(json: unknown): json is ApiSuccessEnvelope<T> {
  return !!json && typeof json === "object" && (json as Record<string, unknown>).success === true && "data" in (json as object);
}

export function isProblemDetail(json: unknown): json is ProblemDetailBody {
  return !!json && typeof json === "object" && typeof (json as Record<string, unknown>).error_code === "string";
}

export async function safeParseJson(response: Response): Promise<unknown> {
  const text = await response.text();
  if (!text) return null;
  try {
    return JSON.parse(text);
  } catch {
    return null;
  }
}
