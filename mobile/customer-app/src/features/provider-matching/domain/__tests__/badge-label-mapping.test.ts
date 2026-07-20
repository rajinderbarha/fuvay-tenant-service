import { resolveBadgeTranslationKey } from "../badge-label-mapping";
import { logger } from "../../../../observability/logger";

jest.mock("../../../../observability/logger", () => ({
  logger: { warn: jest.fn() },
}));

describe("resolveBadgeTranslationKey", () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  it("maps each of the real three known badge strings to a translation key", () => {
    expect(resolveBadgeTranslationKey("Verified")).toBe("providerMatch.badge.verified");
    expect(resolveBadgeTranslationKey("Highly Rated")).toBe("providerMatch.badge.highlyRated");
    expect(resolveBadgeTranslationKey("High Completion")).toBe("providerMatch.badge.highCompletion");
    expect(logger.warn).not.toHaveBeenCalled();
  });

  it("fails safe on an unrecognized badge string: returns null and logs once, never throws", () => {
    expect(() => resolveBadgeTranslationKey("Future Badge")).not.toThrow();
    expect(resolveBadgeTranslationKey("Future Badge")).toBeNull();
    expect(logger.warn).toHaveBeenCalledWith("provider_badge_unmapped", { badge: "Future Badge" });
  });
});
