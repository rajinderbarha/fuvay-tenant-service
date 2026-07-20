/**
 * Mirrors the real backend's own validation exactly — see
 * app/engines/serviceability/schemas.py#AddressCreate and
 * service.py#create_address (zipcode/city required at the service layer
 * too). UX-only: the backend independently re-validates every field
 * (CUSTOMER-L5-07 §63).
 */
export interface AddressFormValues {
  name: string;
  phone: string;
  addressLine1: string;
  addressLine2: string;
  landmark: string;
  city: string;
  district: string;
  state: string;
  zipcode: string;
}

export interface AddressFormErrors {
  addressLine1?: string;
  city?: string;
  state?: string;
  zipcode?: string;
}

// eslint-disable-next-line no-control-regex -- deliberately stripping ASCII control characters, not matching a literal range.
const CONTROL_CHARACTERS = /[\x00-\x1F\x7F]/g;

export function sanitizeAddressText(raw: string, maxLength: number): string {
  return raw.replace(CONTROL_CHARACTERS, "").replace(/\s+/g, " ").trim().slice(0, maxLength);
}

export function validateAddressForm(values: AddressFormValues): AddressFormErrors {
  const errors: AddressFormErrors = {};
  if (values.addressLine1.trim().length < 2) errors.addressLine1 = "required";
  if (values.city.trim().length < 1) errors.city = "required";
  if (values.state.trim().length < 1) errors.state = "required";
  if (values.zipcode.trim().length < 1) errors.zipcode = "required";
  return errors;
}

export function isAddressFormValid(errors: AddressFormErrors): boolean {
  return Object.keys(errors).length === 0;
}
