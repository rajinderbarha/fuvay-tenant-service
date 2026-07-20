import { isValidPhone, isValidOtp, normalizePhone } from "../phone-validation";

describe("isValidPhone", () => {
  it.each(["+919876543210", "9876543210", "+14155552671"])("accepts %s", (phone) => expect(isValidPhone(phone)).toBe(true));
  it.each(["123", "abcdefghij", "", "+0123456789", "0987654321012345678"])("rejects %s", (phone) => expect(isValidPhone(phone)).toBe(false));
});

describe("isValidOtp", () => {
  it.each(["123456", "000000"])("accepts %s", (otp) => expect(isValidOtp(otp)).toBe(true));
  it.each(["12345", "1234567", "abcdef", ""])("rejects %s", (otp) => expect(isValidOtp(otp)).toBe(false));
});

describe("normalizePhone", () => {
  it("strips whitespace and hyphens", () => {
    expect(normalizePhone(" +91 987-654-3210 ")).toBe("+919876543210");
  });
});
