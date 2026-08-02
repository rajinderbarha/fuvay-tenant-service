import React from "react";
import { renderHook, act, waitFor } from "@testing-library/react-native";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { useJobDetail } from "../useJobDetail";

jest.mock("../../../services/jobDetail/jobDetailApi");
jest.mock("../../../navigation/session/SessionProvider", () => ({
  useSession: () => ({ accessContext: { tenantId: "t1", technicianId: "st1" } }),
}));

import * as jobDetailApi from "../../../services/jobDetail/jobDetailApi";

function wrapper({ children }: { children: React.ReactNode }) {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return <QueryClientProvider client={client}>{children}</QueryClientProvider>;
}

beforeEach(() => jest.clearAllMocks());

describe("useJobDetail (spec sections 8, 17)", () => {
  it("fetches job detail scoped by tenant/technician/job", async () => {
    (jobDetailApi.getJobDetail as jest.Mock).mockResolvedValue({ ok: true, data: { job: { job_id: "j1" } } });
    const { result } = renderHook(() => useJobDetail("j1"), { wrapper });
    await waitFor(() => expect(result.current.isLoading).toBe(false));
    expect(jobDetailApi.getJobDetail).toHaveBeenCalledWith("j1", expect.anything());
    expect(result.current.data).toEqual({ job: { job_id: "j1" } });
  });

  it("startTravel invalidates and refetches instead of mutating state locally (never optimistic)", async () => {
    (jobDetailApi.getJobDetail as jest.Mock).mockResolvedValue({ ok: true, data: { job: { job_id: "j1" }, revision: 1 } });
    (jobDetailApi.startTravel as jest.Mock).mockResolvedValue({ ok: true, data: {} });
    const { result } = renderHook(() => useJobDetail("j1"), { wrapper });
    await waitFor(() => expect(result.current.isLoading).toBe(false));

    await act(async () => { await result.current.startTravel(); });

    expect(jobDetailApi.startTravel).toHaveBeenCalledWith("j1");
    // Refetch happened (getJobDetail called again after the mutation) rather than local state edit.
    expect((jobDetailApi.getJobDetail as jest.Mock).mock.calls.length).toBeGreaterThanOrEqual(2);
  });

  it("guards against duplicate submission while a mutation is in flight", async () => {
    (jobDetailApi.getJobDetail as jest.Mock).mockResolvedValue({ ok: true, data: { job: { job_id: "j1" } } });
    let resolveMutation: (v: any) => void = () => {};
    (jobDetailApi.markArrived as jest.Mock).mockReturnValue(new Promise(res => { resolveMutation = res; }));
    const { result } = renderHook(() => useJobDetail("j1"), { wrapper });
    await waitFor(() => expect(result.current.isLoading).toBe(false));

    act(() => { result.current.markArrived(); });
    act(() => { result.current.markArrived(); }); // duplicate press while mutating

    expect(jobDetailApi.markArrived).toHaveBeenCalledTimes(1);
    await act(async () => { resolveMutation({ ok: true, data: {} }); });
  });

  it("surfaces a mutation error without throwing", async () => {
    (jobDetailApi.getJobDetail as jest.Mock).mockResolvedValue({ ok: true, data: { job: { job_id: "j1" } } });
    (jobDetailApi.acceptJob as jest.Mock).mockResolvedValue({ ok: false, error: { code: "CONFLICT", safeMessage: "Already accepted." } });
    const { result } = renderHook(() => useJobDetail("j1"), { wrapper });
    await waitFor(() => expect(result.current.isLoading).toBe(false));

    await act(async () => { await result.current.acceptJob(); });

    expect(result.current.mutationError).toEqual({ code: "CONFLICT", safeMessage: "Already accepted." });
  });
});
