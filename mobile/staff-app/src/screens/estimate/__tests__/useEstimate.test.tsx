import React from "react";
import { renderHook, act, waitFor } from "@testing-library/react-native";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { useEstimate } from "../useEstimate";

jest.mock("../../../services/estimate/estimateApi");
import * as estimateApi from "../../../services/estimate/estimateApi";

function wrapper({ children }: { children: React.ReactNode }) {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return <QueryClientProvider client={client}>{children}</QueryClientProvider>;
}

beforeEach(() => jest.clearAllMocks());

describe("useEstimate (spec sections 5, 11, 17)", () => {
  it("fetches the estimate projection for the job", async () => {
    (estimateApi.getEstimateDetail as jest.Mock).mockResolvedValue({ ok: true, data: { job: { job_id: "j1" }, quote: null } });
    const { result } = renderHook(() => useEstimate("j1"), { wrapper });
    await waitFor(() => expect(result.current.isLoading).toBe(false));
    expect(estimateApi.getEstimateDetail).toHaveBeenCalledWith("j1", expect.anything());
  });

  it("createEstimate refetches rather than fabricating a local quote (never optimistic)", async () => {
    (estimateApi.getEstimateDetail as jest.Mock).mockResolvedValue({ ok: true, data: { job: { job_id: "j1" }, quote: null } });
    (estimateApi.createEstimate as jest.Mock).mockResolvedValue({ ok: true, data: {} });
    const { result } = renderHook(() => useEstimate("j1"), { wrapper });
    await waitFor(() => expect(result.current.isLoading).toBe(false));

    await act(async () => { await result.current.createEstimate(); });

    expect(estimateApi.createEstimate).toHaveBeenCalledWith("j1");
    expect((estimateApi.getEstimateDetail as jest.Mock).mock.calls.length).toBeGreaterThanOrEqual(2);
  });

  it("guards against a duplicate submission while one mutation is in flight", async () => {
    (estimateApi.getEstimateDetail as jest.Mock).mockResolvedValue({ ok: true, data: { job: { job_id: "j1" }, quote: null } });
    let resolveSend: (v: any) => void = () => {};
    (estimateApi.sendEstimateForApproval as jest.Mock).mockReturnValue(new Promise(res => { resolveSend = res; }));
    const { result } = renderHook(() => useEstimate("j1"), { wrapper });
    await waitFor(() => expect(result.current.isLoading).toBe(false));

    act(() => { result.current.sendForApproval("q1"); });
    act(() => { result.current.sendForApproval("q1"); });

    expect(estimateApi.sendEstimateForApproval).toHaveBeenCalledTimes(1);
    await act(async () => { resolveSend({ ok: true, data: {} }); });
  });

  it("surfaces a mutation error without throwing", async () => {
    (estimateApi.getEstimateDetail as jest.Mock).mockResolvedValue({ ok: true, data: { job: { job_id: "j1" }, quote: null } });
    (estimateApi.addEstimateItem as jest.Mock).mockResolvedValue({ ok: false, error: { code: "QUOTE_ITEM_INVALID", safeMessage: "Invalid item." } });
    const { result } = renderHook(() => useEstimate("j1"), { wrapper });
    await waitFor(() => expect(result.current.isLoading).toBe(false));

    await act(async () => { await result.current.addItem("q1", { item_type: "labour", item_name: "x", quantity: 1, unit_price: 1 }); });

    expect(result.current.mutationError).toEqual({ code: "QUOTE_ITEM_INVALID", safeMessage: "Invalid item." });
  });
});
