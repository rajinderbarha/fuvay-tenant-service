/**
 * Phone normalization (spec section 7). Display formatting is kept
 * entirely separate from the E.164 value actually submitted to the
 * backend -- `PhoneLoginRequest.phone` validates against
 * `^\+?[1-9]\d{7,14}$` (app/engines/auth/schemas.py), so normalization
 * must always produce a leading `+` and digits only.
 *
 * Only `+91` (India) is wired as the default for this launch (spec
 * section 7: "initial India/Punjab launch") -- this is NOT a permanent
 * assumption; `SUPPORTED_COUNTRY_CODES` is the single place a future
 * country would be added, never hardcoded again at each call site.
 */
export interface CountryCode {
  code: string; // e.g. "+91"
  iso: string; // e.g. "IN"
  label: string;
  nationalDigits: number; // expected length of the national number
}

export const SUPPORTED_COUNTRY_CODES: readonly CountryCode[] = [
  { code: "+91", iso: "IN", label: "India (+91)", nationalDigits: 10 },
];

export const DEFAULT_COUNTRY_CODE = SUPPORTED_COUNTRY_CODES[0];

/** Strips everything but digits from a national-number display value. */
export function sanitizeNationalNumber(raw: string): string {
  return raw.replace(/\D/g, "");
}

export function isValidNationalNumber(nationalNumber: string, country: CountryCode = DEFAULT_COUNTRY_CODE): boolean {
  return nationalNumber.length === country.nationalDigits;
}

/** Produces the exact E.164 string the backend's regex accepts --
 * `^\+?[1-9]\d{7,14}$`. */
export function toE164(nationalNumber: string, country: CountryCode = DEFAULT_COUNTRY_CODE): string {
  return `${country.code}${nationalNumber}`;
}

/** Masks the national number down to its last 5 digits for on-screen
 * display (matches the design's `+91 ••••• 43210`) -- never used for
 * anything except display; the submitted value always comes from
 * `toE164`. */
export function maskPhoneForDisplay(e164: string, country: CountryCode = DEFAULT_COUNTRY_CODE): string {
  const nationalNumber = e164.startsWith(country.code) ? e164.slice(country.code.length) : e164;
  const visibleCount = Math.min(5, nationalNumber.length);
  const hiddenCount = Math.max(0, nationalNumber.length - visibleCount);
  return `${country.code} ${"•".repeat(hiddenCount)}${nationalNumber.slice(-visibleCount)}`;
}
