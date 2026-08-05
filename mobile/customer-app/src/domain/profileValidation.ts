/**
 * Full-name validation matching `UpdateUserProfileRequest.full_name`
 * (`app/engines/profile/schemas.py`: `Field(None, min_length=2,
 * max_length=255)`) -- no stricter/looser client rule than the backend's
 * own constraint. Unicode names (Punjabi/Hindi/etc.) are explicitly
 * supported; only control characters are rejected.
 */
const MIN_LENGTH = 2;
const MAX_LENGTH = 255;
const CONTROL_CHAR_CODES_MAX = 0x1f;
const DEL_CHAR_CODE = 0x7f;

function containsControlCharacters(value: string): boolean {
  for (let i = 0; i < value.length; i++) {
    const code = value.charCodeAt(i);
    if (code <= CONTROL_CHAR_CODES_MAX || code === DEL_CHAR_CODE) return true;
  }
  return false;
}

export function normalizeFullName(raw: string): string {
  return raw.trim().replace(/\s+/g, " ");
}

export interface FullNameValidationResult {
  valid: boolean;
  error: string | null;
}

export function validateFullName(raw: string): FullNameValidationResult {
  const normalized = normalizeFullName(raw);
  if (containsControlCharacters(raw)) {
    return { valid: false, error: "Name contains invalid characters." };
  }
  if (normalized.length < MIN_LENGTH) {
    return { valid: false, error: `Name must be at least ${MIN_LENGTH} characters.` };
  }
  if (normalized.length > MAX_LENGTH) {
    return { valid: false, error: `Name must be ${MAX_LENGTH} characters or fewer.` };
  }
  return { valid: true, error: null };
}
