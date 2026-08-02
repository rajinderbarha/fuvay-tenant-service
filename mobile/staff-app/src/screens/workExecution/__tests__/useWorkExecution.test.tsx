import React from "react";
import { renderHook, act, waitFor } from "@testing-library/react-native";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { useWorkExecution } from "../useWorkExecution";

jest.mock("../../../services/workExecution/workExecutionApi");
import * as workExecutionApi from "../../../services/workExecution/workExecutionApi";

function wrapper({ children }: { children: React.ReactNode }) {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return <QueryClientProvider client={client}>{children}</QueryClientProvider>;
}

beforeEach(() => jest.clearAllMocks());

describe("useWorkExecution (spec sections 6, 7, 15, 16)", () => {
  it("fetches the work-execution projection for the job", async () => {
    (workExecutionApi.getWorkExecutionDetail as jest.Mock).mockResolvedValue({ ok: true, data: { job: { job_id: "j1" }, work_session: null } });
    const { result } = renderHook(() => useWorkExecution("j1"), { wrapper });
    await waitFor(() => expect(result.current.isLoading).toBe(false));
    expect(workExecutionApi.getWorkExecutionDetail).toHaveBeenCalledWith("j1", expect.anything());
  });

  it("startWork refetches rather than fabricating session state locally (never optimistic)", async () => {
    (workExecutionApi.getWorkExecutionDetail as jest.Mock).mockResolvedValue({ ok: true, data: { job: { job_id: "j1" }, work_session: null } });
    (workExecutionApi.startWork as jest.Mock).mockResolvedValue({ ok: true, data: {} });
    const { result } = renderHook(() => useWorkExecution("j1"), { wrapper });
    await waitFor(() => expect(result.current.isLoading).toBe(false));

    await act(async () => { await result.current.startWork(); });

    expect(workExecutionApi.startWork).toHaveBeenCalledWith("j1");
    expect((workExecutionApi.getWorkExecutionDetail as jest.Mock).mock.calls.length).toBeGreaterThanOrEqual(2);
  });

  it("guards against a duplicate mutation while one is in flight", async () => {
    (workExecutionApi.getWorkExecutionDetail as jest.Mock).mockResolvedValue({ ok: true, data: { job: { job_id: "j1" }, work_session: null } });
    let resolveFinish: (v: any) => void = () => {};
    (workExecutionApi.finishWork as jest.Mock).mockReturnValue(new Promise(res => { resolveFinish = res; }));
    const { result } = renderHook(() => useWorkExecution("j1"), { wrapper });
    await waitFor(() => expect(result.current.isLoading).toBe(false));

    act(() => { result.current.finishWork(); });
    act(() => { result.current.finishWork(); });

    expect(workExecutionApi.finishWork).toHaveBeenCalledTimes(1);
    await act(async () => { resolveFinish({ ok: true, data: {} }); });
  });

  it("surfaces a mutation error without throwing", async () => {
    (workExecutionApi.getWorkExecutionDetail as jest.Mock).mockResolvedValue({ ok: true, data: { job: { job_id: "j1" }, work_session: null } });
    (workExecutionApi.finishWork as jest.Mock).mockResolvedValue({ ok: false, error: { code: "WORK_NOT_READY_TO_FINISH", safeMessage: "Complete every required item first." } });
    const { result } = renderHook(() => useWorkExecution("j1"), { wrapper });
    await waitFor(() => expect(result.current.isLoading).toBe(false));

    await act(async () => { await result.current.finishWork(); });

    expect(result.current.mutationError).toEqual({ code: "WORK_NOT_READY_TO_FINISH", safeMessage: "Complete every required item first." });
  });

  it("requestPart delegates to the reused canonical parts-request endpoint", async () => {
    (workExecutionApi.getWorkExecutionDetail as jest.Mock).mockResolvedValue({ ok: true, data: { job: { job_id: "j1" }, work_session: null } });
    (workExecutionApi.createPartsRequest as jest.Mock).mockResolvedValue({ ok: true, data: {} });
    const { result } = renderHook(() => useWorkExecution("j1"), { wrapper });
    await waitFor(() => expect(result.current.isLoading).toBe(false));

    await act(async () => { await result.current.requestPart({ part_name: "Filter", quantity: 1, estimated_cost: 150, reason: "Clogged" }); });

    expect(workExecutionApi.createPartsRequest).toHaveBeenCalledWith("j1", { part_name: "Filter", quantity: 1, estimated_cost: 150, reason: "Clogged" });
  });
});
