/**
 * Redaction helpers (Phase F spec section 21). Applied before ANY logging,
 * telemetry, or error-report serialization -- never log a raw header/token
 * object directly.
 */
const SENSITIVE_HEADER_NAMES = new Set([
  "authorization", "cookie", "set-cookie", "x-api-key", "x-idempotency-key",
]);

const REDACTED = "[REDACTED]";

/** Returns a redacted copy of a headers record -- never mutates the input. */
export function redactHeaders(headers: Record<string, string>): Record<string, string> {
  const out: Record<string, string> = {};
  for (const [key, value] of Object.entries(headers)) {
    out[key] = SENSITIVE_HEADER_NAMES.has(key.toLowerCase()) ? REDACTED : value;
  }
  return out;
}

const SENSITIVE_KEY_PATTERN = /token|password|secret|otp|mfa_code|refresh|authorization|cookie/i;

/**
 * Deep-redacts an arbitrary object for logging/telemetry -- keys matching
 * SENSITIVE_KEY_PATTERN are replaced regardless of nesting depth. Used for
 * error `cause` fields and any diagnostic payload, never for values shown
 * to the user (those use AppError.safeMessage instead).
 */
export function redactForLogging(value: unknown, depth = 0): unknown {
  if (depth > 6 || value === null || value === undefined) return value;
  if (Array.isArray(value)) return value.map(v => redactForLogging(v, depth + 1));
  if (typeof value === "object") {
    const out: Record<string, unknown> = {};
    for (const [key, v] of Object.entries(value as Record<string, unknown>)) {
      out[key] = SENSITIVE_KEY_PATTERN.test(key) ? REDACTED : redactForLogging(v, depth + 1);
    }
    return out;
  }
  return value;
}

/** Masks all but the last few characters of a raw token-like string, for
 * the rare case a token's presence (not value) needs to appear in a log. */
export function maskToken(token: string | null | undefined): string {
  if (!token) return "(none)";
  if (token.length <= 8) return REDACTED;
  return `${REDACTED}(${token.slice(-4)})`;
}
