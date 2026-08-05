import { parseMoney, addMoney, formatMoney } from "../money";
import { DomainError } from "../errors";

describe("money", () => {
  it("parses a numeric decimal into integer minor units without float drift", () => {
    expect(parseMoney(899.0)).toEqual({ minorUnits: 89900, currency: "INR" });
    expect(parseMoney("1499.00")).toEqual({ minorUnits: 149900, currency: "INR" });
  });

  it("rounds at the paise boundary explicitly", () => {
    expect(parseMoney(10.005).minorUnits).toBe(1001);
  });

  it("throws a DomainError for a non-numeric value instead of coercing", () => {
    expect(() => parseMoney("not-a-number")).toThrow(DomainError);
    expect(() => parseMoney(null)).toThrow(DomainError);
  });

  it("refuses to add Money of different currencies", () => {
    expect(() => addMoney({ minorUnits: 100, currency: "INR" }, { minorUnits: 100, currency: "USD" })).toThrow(DomainError);
  });

  it("adds Money of the same currency", () => {
    expect(addMoney({ minorUnits: 100, currency: "INR" }, { minorUnits: 50, currency: "INR" })).toEqual({
      minorUnits: 150, currency: "INR",
    });
  });

  it("formats for display without becoming a further arithmetic input", () => {
    expect(formatMoney({ minorUnits: 89900, currency: "INR" })).toContain("899");
  });
});
