import { serviceDetailQueryKeys } from "../service-detail-queries";

describe("serviceDetailQueryKeys.detail", () => {
  it("is scoped by category, service, locale and tenant", () => {
    expect(serviceDetailQueryKeys.detail("cat-1", "svc-1", "en", "tenant-1")).toEqual(["service", "detail", "cat-1", "svc-1", "en", "tenant-1"]);
  });

  it("produces distinct keys for different services in the same category", () => {
    const a = serviceDetailQueryKeys.detail("cat-1", "svc-1", "en", undefined);
    const b = serviceDetailQueryKeys.detail("cat-1", "svc-2", "en", undefined);
    expect(a).not.toEqual(b);
  });

  it("produces distinct keys for the same service under a different category (defensive isolation)", () => {
    const a = serviceDetailQueryKeys.detail("cat-1", "svc-1", "en", undefined);
    const b = serviceDetailQueryKeys.detail("cat-2", "svc-1", "en", undefined);
    expect(a).not.toEqual(b);
  });

  it("uses a stable placeholder for an absent tenant", () => {
    expect(serviceDetailQueryKeys.detail("cat-1", "svc-1", "en", undefined)).toEqual(["service", "detail", "cat-1", "svc-1", "en", "no-tenant"]);
  });
});
