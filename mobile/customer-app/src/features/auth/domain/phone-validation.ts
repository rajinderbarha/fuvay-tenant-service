/** Matches the backend's own validation (app/engines/auth/schemas.py: `^\+?[1-9]\d{7,14}$`) so client-side rejection always agrees with the server. */
const PHONE_PATTERN = /^\+?[1-9]\d{7,14}$/;
const OTP_PATTERN = /^\d{6}$/;

export function isValidPhone(phone: string): boolean {
  return PHONE_PATTERN.test(phone.trim());
}

export function isValidOtp(otp: string): boolean {
  return OTP_PATTERN.test(otp.trim());
}

export function normalizePhone(phone: string): string {
  return phone.trim().replace(/[\s-]/g, "");
}
