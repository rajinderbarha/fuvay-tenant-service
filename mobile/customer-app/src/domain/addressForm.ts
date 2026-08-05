/**
 * Add/Edit Address form validation -- mirrors the real backend constraints
 * exactly (`app/engines/serviceability/schemas.py`: `AddressCreate`/
 * `AddressUpdate`), never stricter or looser:
 *   - `label` must be one of ADDRESS_LABELS (added additively this phase,
 *     migration 223 -- distinct from `name`, the recipient's full name).
 *   - `zipcode` must be exactly 6 ASCII digits (backend `_validate_pin`).
 *   - `address_line_1` min 2 / max 300 chars; `city`/`state` required.
 * City/state are never inferred from the PIN client-side -- no confirmed
 * backend geocoding contract exists for customer address entry.
 */
export const ADDRESS_LABELS = ["Home", "Work", "Other"] as const;
export type AddressLabel = (typeof ADDRESS_LABELS)[number];

const CONTROL_CHAR_MAX = 0x1f;
const DEL_CHAR = 0x7f;
const PIN_RE = /^\d{6}$/;

function containsControlCharacters(value: string): boolean {
  for (let i = 0; i < value.length; i++) {
    const code = value.charCodeAt(i);
    if (code <= CONTROL_CHAR_MAX || code === DEL_CHAR) return true;
  }
  return false;
}

export function normalizeAddressText(raw: string): string {
  return raw.trim().replace(/\s+/g, " ");
}

export interface FieldValidationResult {
  valid: boolean;
  error: string | null;
}

function textField(raw: string, { min, max, required }: { min: number; max: number; required: boolean }): FieldValidationResult {
  const normalized = normalizeAddressText(raw);
  if (containsControlCharacters(raw)) return { valid: false, error: "This field contains invalid characters." };
  if (!required && normalized.length === 0) return { valid: true, error: null };
  if (normalized.length < min) return { valid: false, error: `Must be at least ${min} characters.` };
  if (normalized.length > max) return { valid: false, error: `Must be ${max} characters or fewer.` };
  return { valid: true, error: null };
}

export function validateFullName(raw: string): FieldValidationResult {
  return textField(raw, { min: 2, max: 100, required: false });
}

export function validateAddressLine1(raw: string): FieldValidationResult {
  return textField(raw, { min: 2, max: 300, required: true });
}

export function validateCity(raw: string): FieldValidationResult {
  return textField(raw, { min: 1, max: 100, required: true });
}

export function validateState(raw: string): FieldValidationResult {
  return textField(raw, { min: 1, max: 100, required: true });
}

export function validatePinCode(raw: string): FieldValidationResult {
  const normalized = raw.trim();
  if (normalized.length === 0) return { valid: false, error: "PIN code is required." };
  if (!PIN_RE.test(normalized)) return { valid: false, error: "Enter a valid 6-digit PIN code." };
  return { valid: true, error: null };
}

export interface AddressFormState {
  label: AddressLabel;
  fullName: string;
  addressLine1: string;
  addressLine2: string;
  landmark: string;
  city: string;
  state: string;
  pinCode: string;
  isDefault: boolean;
}

export interface AddressFormErrors {
  fullName: string | null;
  addressLine1: string | null;
  city: string | null;
  state: string | null;
  pinCode: string | null;
}

export function validateAddressForm(form: AddressFormState): { errors: AddressFormErrors; valid: boolean } {
  const errors: AddressFormErrors = {
    fullName: validateFullName(form.fullName).error,
    addressLine1: validateAddressLine1(form.addressLine1).error,
    city: validateCity(form.city).error,
    state: validateState(form.state).error,
    pinCode: validatePinCode(form.pinCode).error,
  };
  const valid = Object.values(errors).every(e => e === null);
  return { errors, valid };
}

/** Explicit payload allowlist -- only real backend fields are ever sent,
 * never a UI-only concept (spec section 7). */
export interface AddressCreatePayload {
  label: string;
  name: string | null;
  address_line_1: string;
  address_line_2: string | null;
  landmark: string | null;
  city: string;
  state: string;
  zipcode: string;
  is_default: boolean;
}

export function buildAddressCreatePayload(form: AddressFormState): AddressCreatePayload {
  const fullName = normalizeAddressText(form.fullName);
  const line2 = normalizeAddressText(form.addressLine2);
  const landmark = normalizeAddressText(form.landmark);
  return {
    label: form.label,
    name: fullName.length > 0 ? fullName : null,
    address_line_1: normalizeAddressText(form.addressLine1),
    address_line_2: line2.length > 0 ? line2 : null,
    landmark: landmark.length > 0 ? landmark : null,
    city: normalizeAddressText(form.city),
    state: normalizeAddressText(form.state),
    zipcode: form.pinCode.trim(),
    is_default: form.isDefault,
  };
}

export type AddressUpdatePayload = Partial<AddressCreatePayload>;

/** Only fields that actually changed vs. the loaded server values are sent
 * on edit -- never the full form, and `is_default` is included only when
 * the customer is turning it ON (spec section 4: the server-owned default
 * invariant never accepts an explicit "un-default" through this form). */
export function buildAddressUpdatePayload(
  form: AddressFormState,
  original: AddressFormState,
): AddressUpdatePayload {
  const full = buildAddressCreatePayload(form);
  const originalFull = buildAddressCreatePayload(original);
  const payload: AddressUpdatePayload = {};
  (Object.keys(full) as (keyof AddressCreatePayload)[]).forEach(key => {
    if (key === "is_default") {
      if (full.is_default && !originalFull.is_default) payload.is_default = true;
      return;
    }
    if (full[key] !== originalFull[key]) {
      (payload as Record<string, unknown>)[key] = full[key];
    }
  });
  return payload;
}

export function isAddressFormDirty(form: AddressFormState, original: AddressFormState): boolean {
  return Object.keys(buildAddressUpdatePayload(form, original)).length > 0;
}
