import {
  validatePinCode, validateAddressLine1, validateCity, validateState, validateFullName,
  validateAddressForm, buildAddressCreatePayload, buildAddressUpdatePayload, isAddressFormDirty,
  AddressFormState,
} from "../addressForm";

function form(overrides: Partial<AddressFormState> = {}): AddressFormState {
  return {
    label: "Home", fullName: "Rajinder Singh", addressLine1: "House 24",
    addressLine2: "Model Town", landmark: "", city: "Ludhiana", state: "Punjab",
    pinCode: "141002", isDefault: false,
    ...overrides,
  };
}

describe("validatePinCode", () => {
  it("accepts exactly six ASCII digits", () => {
    expect(validatePinCode("141002").valid).toBe(true);
  });
  it("rejects fewer than six digits", () => {
    expect(validatePinCode("12345").valid).toBe(false);
  });
  it("rejects non-digit characters", () => {
    expect(validatePinCode("ABCDEF").valid).toBe(false);
  });
  it("rejects empty", () => {
    expect(validatePinCode("").valid).toBe(false);
  });
});

describe("validateAddressLine1/City/State", () => {
  it("requires address line 1", () => {
    expect(validateAddressLine1("").valid).toBe(false);
  });
  it("requires city", () => {
    expect(validateCity("").valid).toBe(false);
  });
  it("requires state", () => {
    expect(validateState("").valid).toBe(false);
  });
  it("supports Unicode text", () => {
    expect(validateAddressLine1("मकान नंबर 24").valid).toBe(true);
    expect(validateCity("लुधियाना").valid).toBe(true);
  });
  it("rejects control characters", () => {
    const withControlChar = "House" + String.fromCharCode(7) + "24";
    expect(validateAddressLine1(withControlChar).valid).toBe(false);
  });
});

describe("validateFullName", () => {
  it("is optional -- empty is valid", () => {
    expect(validateFullName("").valid).toBe(true);
  });
  it("rejects a single character when provided", () => {
    expect(validateFullName("R").valid).toBe(false);
  });
});

describe("validateAddressForm", () => {
  it("passes for a fully valid form", () => {
    expect(validateAddressForm(form()).valid).toBe(true);
  });
  it("fails when PIN code is invalid", () => {
    const result = validateAddressForm(form({ pinCode: "123" }));
    expect(result.valid).toBe(false);
    expect(result.errors.pinCode).not.toBeNull();
  });
});

describe("buildAddressCreatePayload", () => {
  it("builds an explicit allowlist payload with only real backend fields", () => {
    const payload = buildAddressCreatePayload(form());
    expect(payload).toEqual({
      label: "Home", name: "Rajinder Singh", address_line_1: "House 24",
      address_line_2: "Model Town", landmark: null, city: "Ludhiana", state: "Punjab",
      zipcode: "141002", is_default: false,
    });
  });
  it("normalizes surrounding whitespace without truncating", () => {
    const payload = buildAddressCreatePayload(form({ addressLine1: "  House 24  " }));
    expect(payload.address_line_1).toBe("House 24");
  });
  it("omits an empty optional landmark/line2 as null rather than an empty string", () => {
    const payload = buildAddressCreatePayload(form({ addressLine2: "   ", landmark: "" }));
    expect(payload.address_line_2).toBeNull();
    expect(payload.landmark).toBeNull();
  });
});

describe("buildAddressUpdatePayload / isAddressFormDirty", () => {
  it("is empty when nothing changed", () => {
    const original = form();
    expect(buildAddressUpdatePayload(original, original)).toEqual({});
    expect(isAddressFormDirty(original, original)).toBe(false);
  });
  it("includes only the fields that changed", () => {
    const original = form();
    const edited = form({ landmark: "Near Bus Stand" });
    const payload = buildAddressUpdatePayload(edited, original);
    expect(payload).toEqual({ landmark: "Near Bus Stand" });
    expect(isAddressFormDirty(edited, original)).toBe(true);
  });
  it("includes is_default only when turning it ON, never turning it off", () => {
    const original = form({ isDefault: true });
    const edited = form({ isDefault: false });
    const payload = buildAddressUpdatePayload(edited, original);
    expect(payload.is_default).toBeUndefined();
  });
  it("includes is_default when turning it on", () => {
    const original = form({ isDefault: false });
    const edited = form({ isDefault: true });
    const payload = buildAddressUpdatePayload(edited, original);
    expect(payload.is_default).toBe(true);
  });
});
