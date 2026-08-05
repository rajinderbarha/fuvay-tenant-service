import { sanitizeNationalNumber, isValidNationalNumber, toE164, maskPhoneForDisplay, DEFAULT_COUNTRY_CODE } from "../phone";

describe("phone", () => {
  it("sanitizes non-digit characters from a national number", () => {
    expect(sanitizeNationalNumber("98765 43210")).toBe("9876543210");
    expect(sanitizeNationalNumber("(987) 654-3210")).toBe("9876543210");
  });

  it("validates a well-formed 10-digit Indian mobile number", () => {
    expect(isValidNationalNumber("9876543210")).toBe(true);
  });

  it("rejects a mobile number of the wrong length", () => {
    expect(isValidNationalNumber("987654321")).toBe(false);
    expect(isValidNationalNumber("98765432100")).toBe(false);
  });

  it("produces the exact E.164 format the backend regex accepts", () => {
    expect(toE164("9876543210")).toBe("+919876543210");
  });

  it("masks all but the last 5 digits for display", () => {
    expect(maskPhoneForDisplay("+919876543210")).toBe(`${DEFAULT_COUNTRY_CODE.code} •••••43210`);
  });
});
