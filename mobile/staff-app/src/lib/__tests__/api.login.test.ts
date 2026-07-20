import { authApi } from "../api";

// UX-05B FIX 1 regression: authApi.login previously called the nonexistent
// POST /v1/auth/staff/login with {phone,password} (405, not in the OpenAPI
// spec). This asserts it now calls the real, confirmed-live contract:
// POST /v1/auth/login with {email,password}, and that the real response
// envelope ({access_token,refresh_token,user,tenant}, unwrapped from
// {data:...} by apiFetch) round-trips correctly.
describe("authApi.login", () => {
  beforeEach(() => { jest.resetModules(); });

  it("POSTs to /v1/auth/login with {email,password} and returns the real response shape", async () => {
    const fakeResponse = {
      data: {
        access_token: "tok-123",
        refresh_token: "refresh-123",
        user: {
          id: "staff-1", user_id: "staff-1", email: "tech2@demo-ac-services.local",
          phone: null, full_name: "Technician Two", role: "technician",
          tenant_id: "5209ef33-a53e-4fc0-b3f6-006335b8d712", is_active: true,
        },
        tenant: { id: "5209ef33-a53e-4fc0-b3f6-006335b8d712", name: "Demo AC Services" },
      },
    };
    const fetchMock = jest.fn().mockResolvedValue({
      ok: true,
      json: () => Promise.resolve(fakeResponse),
    });
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    (global as any).fetch = fetchMock;

    const result = await authApi.login("tech2@demo-ac-services.local", "Password123!");

    expect(fetchMock).toHaveBeenCalledTimes(1);
    const [url, options] = fetchMock.mock.calls[0];
    expect(url).toMatch(/\/v1\/auth\/login$/);
    expect(url).not.toMatch(/staff\/login/);
    const body = JSON.parse(options.body);
    expect(body).toEqual({ email: "tech2@demo-ac-services.local", password: "Password123!" });
    expect(body.phone).toBeUndefined();

    expect(result.access_token).toBe("tok-123");
    expect(result.user.full_name).toBe("Technician Two");
    expect(result.user.email).toBe("tech2@demo-ac-services.local");
  });
});
