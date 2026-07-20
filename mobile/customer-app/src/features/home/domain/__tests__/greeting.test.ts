import { dayPeriodFromHour, safeFirstName } from "../greeting";

describe("dayPeriodFromHour", () => {
  it.each([
    [6, "morning"],
    [11, "morning"],
    [12, "afternoon"],
    [16, "afternoon"],
    [17, "evening"],
    [23, "evening"],
  ])("hour %i -> %s", (hour, expected) => {
    expect(dayPeriodFromHour(hour)).toBe(expected);
  });
});

describe("safeFirstName", () => {
  it("returns the first word of a full name", () => {
    expect(safeFirstName("Jane Doe")).toBe("Jane");
  });

  it("returns null for null/undefined/empty input", () => {
    expect(safeFirstName(null)).toBeNull();
    expect(safeFirstName(undefined)).toBeNull();
    expect(safeFirstName("")).toBeNull();
    expect(safeFirstName("   ")).toBeNull();
  });

  it("returns null for an implausibly long first token (malformed data)", () => {
    expect(safeFirstName("x".repeat(50))).toBeNull();
  });
});
