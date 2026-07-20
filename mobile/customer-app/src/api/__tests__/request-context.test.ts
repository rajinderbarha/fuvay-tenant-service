import { setRequestLocale, getRequestLocale, setRequestTenantId, getRequestTenantId, buildRequestHeaders } from "../request-context";

describe("request-context locale/tenant scoping", () => {
  afterEach(() => {
    setRequestLocale("en");
    setRequestTenantId(undefined);
  });

  it("defaults to the app's configured default locale", () => {
    expect(getRequestLocale()).toBe("en");
  });

  it("reflects the most recently set locale", () => {
    setRequestLocale("hi");
    expect(getRequestLocale()).toBe("hi");
  });

  it("includes the current locale in the Accept-Language header", async () => {
    setRequestLocale("pa");
    const headers = await buildRequestHeaders();
    expect(headers["Accept-Language"]).toBe("pa");
  });

  it("has no tenant id by default", () => {
    expect(getRequestTenantId()).toBeUndefined();
  });

  it("includes X-Tenant-Id only when a tenant is set", async () => {
    const withoutTenant = await buildRequestHeaders();
    expect(withoutTenant["X-Tenant-Id"]).toBeUndefined();

    setRequestTenantId("tenant-123");
    expect(getRequestTenantId()).toBe("tenant-123");
    const withTenant = await buildRequestHeaders();
    expect(withTenant["X-Tenant-Id"]).toBe("tenant-123");
  });
});
