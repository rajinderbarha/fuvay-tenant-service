import React from "react";
import { renderHook, act, waitFor } from "@testing-library/react-native";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { useDirectPayment } from "../useDirectPayment";

jest.mock("../../../services/directPayment/directPaymentApi");
import * as api from "../../../services/directPayment/directPaymentApi";

function wrapper({ children }: { children: React.ReactNode }) {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return <QueryClientProvider client={client}>{children}</QueryClientProvider>;
}

beforeEach(() => jest.clearAllMocks());

describe("useDirectPayment (spec sections 6, 13, 14, 17)", () => {
  it("fetches the direct-payment projection for the job", async () => {
    (api.getDirectPaymentDetail as jest.Mock).mockResolvedValue({ ok: true, data: { job: { job_id: "j1" }, provider_record: null } });
    const { result } = renderHook(() => useDirectPayment("j1"), { wrapper });
    await waitFor(() => expect(result.current.isLoading).toBe(false));
    expect(api.getDirectPaymentDetail).toHaveBeenCalledWith("j1", expect.anything());
  });

  it("declarePayment refetches rather than fabricating confirmation locally (never optimistic)", async () => {
    (api.getDirectPaymentDetail as jest.Mock).mockResolvedValue({ ok: true, data: { job: { job_id: "j1" }, provider_record: null } });
    (api.declarePayment as jest.Mock).mockResolvedValue({ ok: true, data: {} });
    const { result } = renderHook(() => useDirectPayment("j1"), { wrapper });
    await waitFor(() => expect(result.current.isLoading).toBe(false));

    await act(async () => { await result.current.declarePayment({ amount: "1701.00", method: "onsite_cash" }); });

    expect(api.declarePayment).toHaveBeenCalledWith("j1", { amount: "1701.00", method: "onsite_cash" });
    expect((api.getDirectPaymentDetail as jest.Mock).mock.calls.length).toBeGreaterThanOrEqual(2);
  });

  it("guards against a duplicate finalize while one is in flight", async () => {
    (api.getDirectPaymentDetail as jest.Mock).mockResolvedValue({ ok: true, data: { job: { job_id: "j1" }, provider_record: null } });
    let resolveFinalize: (v: any) => void = () => {};
    (api.finalizeJob as jest.Mock).mockReturnValue(new Promise(res => { resolveFinalize = res; }));
    const { result } = renderHook(() => useDirectPayment("j1"), { wrapper });
    await waitFor(() => expect(result.current.isLoading).toBe(false));

    act(() => { result.current.finalizeJob(); });
    act(() => { result.current.finalizeJob(); });

    expect(api.finalizeJob).toHaveBeenCalledTimes(1);
    await act(async () => { resolveFinalize({ ok: true, data: {} }); });
  });

  it("surfaces a mutation error without throwing", async () => {
    (api.getDirectPaymentDetail as jest.Mock).mockResolvedValue({ ok: true, data: { job: { job_id: "j1" }, provider_record: null } });
    (api.finalizeJob as jest.Mock).mockResolvedValue({ ok: false, error: { code: "JOB_NOT_READY_TO_FINALIZE", safeMessage: "Every closure requirement must pass first." } });
    const { result } = renderHook(() => useDirectPayment("j1"), { wrapper });
    await waitFor(() => expect(result.current.isLoading).toBe(false));

    await act(async () => { await result.current.finalizeJob(); });

    expect(result.current.mutationError).toEqual({ code: "JOB_NOT_READY_TO_FINALIZE", safeMessage: "Every closure requirement must pass first." });
  });
});
