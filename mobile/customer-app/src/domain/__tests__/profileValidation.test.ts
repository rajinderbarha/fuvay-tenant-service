import { validateFullName, normalizeFullName } from "../profileValidation";

describe("normalizeFullName", () => {
  it("trims and collapses repeated whitespace", () => {
    expect(normalizeFullName("  Rajinder   Singh  ")).toBe("Rajinder Singh");
  });
});

describe("validateFullName", () => {
  it("accepts a real Punjabi/Unicode name", () => {
    expect(validateFullName("ਰਾਜਿੰਦਰ ਸਿੰਘ").valid).toBe(true);
  });

  it("accepts a Hindi name", () => {
    expect(validateFullName("राजिंदर सिंह").valid).toBe(true);
  });

  it("rejects a name shorter than the backend's min_length=2", () => {
    const result = validateFullName("R");
    expect(result.valid).toBe(false);
    expect(result.error).toContain("at least 2");
  });

  it("rejects a name longer than the backend's max_length=255", () => {
    const result = validateFullName("A".repeat(256));
    expect(result.valid).toBe(false);
  });

  it("rejects control characters", () => {
    const result = validateFullName("Rajinder\x00Singh");
    expect(result.valid).toBe(false);
  });

  it("never restricts names to ASCII", () => {
    expect(validateFullName("José García").valid).toBe(true);
  });

  it("treats a whitespace-only name as too short after normalization", () => {
    expect(validateFullName("   ").valid).toBe(false);
  });
});
