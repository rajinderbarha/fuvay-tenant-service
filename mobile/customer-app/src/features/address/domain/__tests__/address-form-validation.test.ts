import { sanitizeAddressText, validateAddressForm, isAddressFormValid, type AddressFormValues } from "../address-form-validation";

const validValues: AddressFormValues = {
  name: "Ravi",
  phone: "9876543210",
  addressLine1: "12 MG Road",
  addressLine2: "",
  landmark: "",
  city: "Bengaluru",
  district: "",
  state: "Karnataka",
  zipcode: "560001",
};

describe("sanitizeAddressText", () => {
  it("trims and collapses whitespace", () => {
    expect(sanitizeAddressText("  12   MG Road  ", 300)).toBe("12 MG Road");
  });

  it("strips control characters", () => {
    expect(sanitizeAddressText("12\x00MG Road\x1F", 300)).toBe("12MG Road");
  });

  it("caps length", () => {
    expect(sanitizeAddressText("a".repeat(400), 300)).toHaveLength(300);
  });

  it("preserves Hindi and Punjabi text untouched", () => {
    expect(sanitizeAddressText("बेंगलुरु", 300)).toBe("बेंगलुरु");
  });
});

describe("validateAddressForm", () => {
  it("accepts a fully valid form (matches real backend AddressCreate requirements)", () => {
    expect(validateAddressForm(validValues)).toEqual({});
    expect(isAddressFormValid(validateAddressForm(validValues))).toBe(true);
  });

  it("requires address_line_1 (2+ chars, matching the real backend's min_length=2)", () => {
    const errors = validateAddressForm({ ...validValues, addressLine1: "1" });
    expect(errors.addressLine1).toBeDefined();
  });

  it("requires city", () => {
    const errors = validateAddressForm({ ...validValues, city: "" });
    expect(errors.city).toBeDefined();
  });

  it("requires state", () => {
    const errors = validateAddressForm({ ...validValues, state: "" });
    expect(errors.state).toBeDefined();
  });

  it("requires zipcode", () => {
    const errors = validateAddressForm({ ...validValues, zipcode: "" });
    expect(errors.zipcode).toBeDefined();
  });

  it("does not require name, phone, landmark, district, or address line 2 (all optional in the real backend schema)", () => {
    const errors = validateAddressForm({ ...validValues, name: "", phone: "", landmark: "", district: "", addressLine2: "" });
    expect(isAddressFormValid(errors)).toBe(true);
  });
});
