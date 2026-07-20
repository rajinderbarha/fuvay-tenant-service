import { parseDeepLink } from "../deep-link-parser";

describe("parseDeepLink", () => {
  it("parses a custom-scheme URL", () => {
    const result = parseDeepLink("serviceos://bookings/abc123");
    expect(result.ok).toBe(true);
    if (result.ok) {
      expect(result.link.scheme).toBe("serviceos");
      expect(result.link.path).toBe("bookings/abc123");
      expect(result.link.source).toBe("custom-scheme");
    }
  });

  it("parses query parameters", () => {
    const result = parseDeepLink("serviceos://home?campaign=diwali&ref=abc");
    expect(result.ok).toBe(true);
    if (result.ok) {
      expect(result.link.query).toEqual({ campaign: "diwali", ref: "abc" });
    }
  });

  it("classifies a trusted https host as a universal link", () => {
    const result = parseDeepLink("https://app.serviceos.in/home");
    expect(result.ok).toBe(true);
    if (result.ok) expect(result.link.source).toBe("universal-link");
  });

  it("classifies an untrusted https host as unknown", () => {
    const result = parseDeepLink("https://evil.example.com/home");
    expect(result.ok).toBe(true);
    if (result.ok) expect(result.link.source).toBe("unknown");
  });

  it("rejects a malformed URL", () => {
    const result = parseDeepLink("not a url");
    expect(result.ok).toBe(false);
  });

  it("rejects an oversized URL", () => {
    const oversized = `serviceos://home?x=${"a".repeat(3000)}`;
    const result = parseDeepLink(oversized);
    expect(result.ok).toBe(false);
    if (!result.ok) expect(result.reason).toBe("oversized_url");
  });
});
