import { resolveModuleRenderer } from "../module-registry";

describe("resolveModuleRenderer", () => {
  it("recognizes the category-grid module type", () => {
    const result = resolveModuleRenderer("category-grid");
    expect(result.recognized).toBe(true);
  });

  it("safely reports an unknown module type as unrecognized instead of throwing", () => {
    const result = resolveModuleRenderer("some-future-module-type");
    expect(result.recognized).toBe(false);
    if (!result.recognized) expect(result.moduleType).toBe("some-future-module-type");
  });

  it("does not crash for an empty string type", () => {
    expect(() => resolveModuleRenderer("")).not.toThrow();
    expect(resolveModuleRenderer("").recognized).toBe(false);
  });
});
