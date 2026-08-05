/**
 * Sensitive-field redaction for logging/telemetry. `logger` (utils/logger)
 * and any future telemetry sink must pass context objects through this
 * before they can be written anywhere -- access tokens, OTPs, full
 * addresses, private message bodies and uploaded-media URLs must never
 * reach a log line or analytics event verbatim.
 */
const SENSITIVE_KEY_PATTERN = /token|otp|password|secret|authorization|address|message|coordinates?|lat|lng|latitude|longitude|media_?url|photo_?url/i;

export function redact<T extends Record<string, unknown>>(context: T): Record<string, unknown> {
  const result: Record<string, unknown> = {};
  for (const [key, value] of Object.entries(context)) {
    if (SENSITIVE_KEY_PATTERN.test(key)) {
      result[key] = "[redacted]";
    } else if (value && typeof value === "object" && !Array.isArray(value)) {
      result[key] = redact(value as Record<string, unknown>);
    } else {
      result[key] = value;
    }
  }
  return result;
}
