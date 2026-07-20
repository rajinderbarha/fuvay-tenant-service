const SENSITIVE_KEY_PATTERN =
  /(authorization|token|access_?token|refresh_?token|otp|password|secret|session_?id|phone|email|address|lat(itude)?|lng|long(itude)?|payment|card_?number|cvv)/i;

const REDACTED = "[redacted]";

/**
 * Recursively redacts sensitive keys from any loggable payload. Used by the
 * logger before anything reaches console/crash-reporting/analytics adapters.
 */
export function redact(value: unknown, depth = 0): unknown {
  if (depth > 6) return REDACTED;

  if (Array.isArray(value)) return value.map((item) => redact(item, depth + 1));

  if (value && typeof value === "object") {
    const output: Record<string, unknown> = {};
    for (const [key, val] of Object.entries(value as Record<string, unknown>)) {
      output[key] = SENSITIVE_KEY_PATTERN.test(key) ? REDACTED : redact(val, depth + 1);
    }
    return output;
  }

  return value;
}
