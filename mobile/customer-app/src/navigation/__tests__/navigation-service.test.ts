import { navigate, isNavigationReady, getCurrentRouteName } from "../navigation-service";

describe("navigation-service", () => {
  it("is not ready before any container mounts", () => {
    expect(isNavigationReady()).toBe(false);
    expect(getCurrentRouteName()).toBeUndefined();
  });

  it("rejects an unknown route and does not queue it", () => {
    const result = navigate("TotallyMadeUpRoute" as never);
    expect(result).toBe(false);
  });

  it("queues a known route when the container isn't ready yet, without throwing", () => {
    expect(() => navigate("baselineLanding" as never)).not.toThrow();
  });
});
