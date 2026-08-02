import { checkPublicHealth } from "../healthApi";

const originalFetch = global.fetch;
afterEach(() => { global.fetch = originalFetch; jest.restoreAllMocks(); });

function mockFetch(response: Partial<Response> & { jsonBody?: unknown }) {
  global.fetch = jest.fn().mockResolvedValue({
    ok: response.ok ?? true,
    json: async () => response.jsonBody,
  } as Response);
}

describe("checkPublicHealth", () => {
  it("maps status:ok -> online", async () => {
    mockFetch({ ok: true, jsonBody: { status: "ok" } });
    expect(await checkPublicHealth()).toBe("online");
  });

  it("maps status:degraded -> limited", async () => {
    mockFetch({ ok: true, jsonBody: { status: "degraded" } });
    expect(await checkPublicHealth()).toBe("limited");
  });

  it("maps status:down -> unavailable", async () => {
    mockFetch({ ok: true, jsonBody: { status: "down" } });
    expect(await checkPublicHealth()).toBe("unavailable");
  });

  it("maps a non-200 response -> unavailable without inspecting the body", async () => {
    mockFetch({ ok: false, jsonBody: {} });
    expect(await checkPublicHealth()).toBe("unavailable");
  });

  it("maps a network exception -> unavailable, never throwing", async () => {
    global.fetch = jest.fn().mockRejectedValue(new Error("network down"));
    await expect(checkPublicHealth()).resolves.toBe("unavailable");
  });

  it("maps an unparseable body -> unavailable", async () => {
    global.fetch = jest.fn().mockResolvedValue({ ok: true, json: async () => { throw new Error("bad json"); } } as unknown as Response);
    expect(await checkPublicHealth()).toBe("unavailable");
  });
});
