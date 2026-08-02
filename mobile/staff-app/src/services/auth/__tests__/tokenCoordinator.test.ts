import {
  getAccessToken, getRefreshToken, getSessionId, getSessionGeneration, isTokenPresent,
  setTokens, establishTokens, clearTokens, __resetTokenCoordinatorForTests,
} from "../tokenCoordinator";

beforeEach(() => __resetTokenCoordinatorForTests());

describe("tokenCoordinator", () => {
  it("starts with no tokens and generation 0", () => {
    expect(isTokenPresent()).toBe(false);
    expect(getSessionGeneration()).toBe(0);
  });

  it("establishTokens sets tokens and bumps the session generation", () => {
    establishTokens({ accessToken: "a1", refreshToken: "r1", sessionId: "s1" });
    expect(getAccessToken()).toBe("a1");
    expect(getRefreshToken()).toBe("r1");
    expect(getSessionId()).toBe("s1");
    expect(getSessionGeneration()).toBe(1);
  });

  it("setTokens (a plain rotation) updates tokens WITHOUT bumping generation", () => {
    establishTokens({ accessToken: "a1", refreshToken: "r1", sessionId: "s1" });
    const genAfterEstablish = getSessionGeneration();
    setTokens({ accessToken: "a2", refreshToken: "r2" });
    expect(getAccessToken()).toBe("a2");
    expect(getSessionGeneration()).toBe(genAfterEstablish);
  });

  it("clearTokens wipes everything and bumps generation (prevents stale in-flight writes)", () => {
    establishTokens({ accessToken: "a1", refreshToken: "r1", sessionId: "s1" });
    const genBefore = getSessionGeneration();
    clearTokens();
    expect(getAccessToken()).toBeNull();
    expect(getRefreshToken()).toBeNull();
    expect(isTokenPresent()).toBe(false);
    expect(getSessionGeneration()).toBe(genBefore + 1);
  });

  it("each establishTokens call is a new generation, so an old generation number is recognizably stale", () => {
    establishTokens({ accessToken: "a1", refreshToken: "r1", sessionId: "s1" });
    const gen1 = getSessionGeneration();
    establishTokens({ accessToken: "a2", refreshToken: "r2", sessionId: "s2" });
    const gen2 = getSessionGeneration();
    expect(gen2).toBeGreaterThan(gen1);
  });
});
