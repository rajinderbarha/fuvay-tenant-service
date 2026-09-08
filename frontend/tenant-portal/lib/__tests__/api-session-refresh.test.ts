import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { apiFetch } from "../api";

const reply = (status: number, body: unknown) => new Response(JSON.stringify(body), { status, headers: { "Content-Type": "application/json" } });

beforeEach(() => {
  localStorage.clear();
  localStorage.setItem("serviceos_tenant_token", "access-old");
  localStorage.setItem("serviceos_tenant_refresh", "refresh-old");
});
afterEach(() => { vi.unstubAllGlobals(); localStorage.clear(); });

describe("session refresh during payment confirmation", () => {
  it("stores the rotated refresh token and uses it on the next expiry", async () => {
    const fetchMock = vi.fn()
      .mockResolvedValueOnce(reply(401, {}))
      .mockResolvedValueOnce(reply(200, { data: { access_token: "access-new", refresh_token: "refresh-new" } }))
      .mockResolvedValueOnce(reply(200, { data: { status: "captured" } }))
      .mockResolvedValueOnce(reply(401, {}))
      .mockResolvedValueOnce(reply(200, { data: { access_token: "access-next", refresh_token: "refresh-next" } }))
      .mockResolvedValueOnce(reply(200, { data: { entitled_seats: 3 } }));
    vi.stubGlobal("fetch", fetchMock);
    const body = JSON.stringify({ razorpay_order_id: "order_paid", razorpay_payment_id: "pay_paid", razorpay_signature: "signed" });
    await expect(apiFetch("/confirm", { method: "POST", body })).resolves.toEqual({ status: "captured" });
    expect(localStorage.getItem("serviceos_tenant_refresh")).toBe("refresh-new");
    expect(fetchMock.mock.calls[2][1]).toMatchObject({ method: "POST", body, headers: { Authorization: "Bearer access-new" } });
    await apiFetch("/seats");
    expect(JSON.parse(fetchMock.mock.calls[4][1].body)).toEqual({ refresh_token: "refresh-new" });
    expect(localStorage.getItem("serviceos_tenant_refresh")).toBe("refresh-next");
  });

  it("shares one refresh across concurrent expired requests", async () => {
    let release!: (response: Response) => void;
    const refresh = new Promise<Response>(resolve => { release = resolve; });
    const fetchMock = vi.fn((url: string, options: RequestInit) => {
      if (url.endsWith("/v1/auth/token/refresh")) return refresh;
      return Promise.resolve(reply((options.headers as Record<string, string>).Authorization === "Bearer access-new" ? 200 : 401, { data: { ok: true } }));
    });
    vi.stubGlobal("fetch", fetchMock);
    const requests = Promise.all([apiFetch("/confirm", { method: "POST" }), apiFetch("/status")]);
    await vi.waitFor(() => expect(fetchMock.mock.calls.filter(([url]) => url.endsWith("/refresh"))).toHaveLength(1));
    release(reply(200, { data: { access_token: "access-new", refresh_token: "refresh-new" } }));
    await expect(requests).resolves.toEqual([{ ok: true }, { ok: true }]);
    expect(fetchMock.mock.calls.filter(([url]) => url.endsWith("/refresh"))).toHaveLength(1);
  });

  it("preserves the session and reports a payment validation error after refresh", async () => {
    vi.stubGlobal("fetch", vi.fn()
      .mockResolvedValueOnce(reply(401, {}))
      .mockResolvedValueOnce(reply(200, { data: { access_token: "access-new", refresh_token: "refresh-new" } }))
      .mockResolvedValueOnce(reply(422, { error_code: "ACTIVATION_PAYMENT_SIGNATURE_INVALID", detail: "Payment signature is invalid." })));
    await expect(apiFetch("/confirm", { method: "POST" })).rejects.toMatchObject({ code: "ACTIVATION_PAYMENT_SIGNATURE_INVALID" });
    expect(localStorage.getItem("serviceos_tenant_token")).toBe("access-new");
  });

  it("retains credentials during a temporary refresh outage", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValueOnce(reply(401, {})).mockResolvedValueOnce(reply(503, {})));
    await expect(apiFetch("/confirm", { method: "POST" })).rejects.toMatchObject({ code: "SESSION_REFRESH_UNAVAILABLE" });
    expect(localStorage.getItem("serviceos_tenant_refresh")).toBe("refresh-old");
  });
});
