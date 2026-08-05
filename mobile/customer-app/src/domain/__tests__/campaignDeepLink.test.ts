import { isAllowedCampaignDeepLink } from "../campaignDeepLink";

describe("campaign deep-link allowlist", () => {
  it("accepts every backend-allowlisted prefix", () => {
    for (const link of ["app://home", "app://category/ac-repair", "app://service/svc-1", "app://booking/b-1", "app://offers"]) {
      expect(isAllowedCampaignDeepLink(link)).toBe(true);
    }
  });

  it("rejects an arbitrary external URL", () => {
    expect(isAllowedCampaignDeepLink("https://evil.example.com")).toBe(false);
  });

  it("rejects null/undefined/empty", () => {
    expect(isAllowedCampaignDeepLink(null)).toBe(false);
    expect(isAllowedCampaignDeepLink(undefined)).toBe(false);
    expect(isAllowedCampaignDeepLink("")).toBe(false);
  });

  it("mirrors the backend's own prefix-startsWith check exactly, including its permissiveness", () => {
    // The backend (app/engines/customer_campaigns/service.py
    // `_validate_deeplink`) also uses plain `startswith`, so "app://homex"
    // is accepted server-side too -- this client check intentionally
    // mirrors that behavior rather than being independently stricter.
    expect(isAllowedCampaignDeepLink("app://homex")).toBe(true);
  });

  it("rejects a prefix that matches no allowlisted entry", () => {
    expect(isAllowedCampaignDeepLink("app://admin/1")).toBe(false);
  });
});
