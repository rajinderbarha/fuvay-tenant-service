import React from "react";
import { renderHook, act, waitFor } from "@testing-library/react-native";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { useSchedule } from "../useSchedule";

jest.mock("../../../services/schedule/scheduleApi");
import * as api from "../../../services/schedule/scheduleApi";

function wrapper({ children }: { children: React.ReactNode }) {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return <QueryClientProvider client={client}>{children}</QueryClientProvider>;
}

beforeEach(() => jest.clearAllMocks());

describe("useSchedule (spec sections 9, 10)", () => {
  it("fetches the week window anchored to the selected date", async () => {
    (api.getSchedule as jest.Mock).mockResolvedValue({ ok: true, data: { days: [], pending_time_off_count: 0, last_synced_at: "" } });
    const { result } = renderHook(() => useSchedule(new Date("2026-07-31T12:00:00")), { wrapper });
    await waitFor(() => expect(result.current.isLoading).toBe(false));
    expect(api.getSchedule).toHaveBeenCalledWith("2026-07-27", "2026-08-02", expect.anything());
  });

  it("addBlockedTime refetches rather than mutating locally", async () => {
    (api.getSchedule as jest.Mock).mockResolvedValue({ ok: true, data: { days: [], pending_time_off_count: 0, last_synced_at: "" } });
    (api.createBlockedTime as jest.Mock).mockResolvedValue({ ok: true, data: {} });
    const { result } = renderHook(() => useSchedule(new Date("2026-07-31T12:00:00")), { wrapper });
    await waitFor(() => expect(result.current.isLoading).toBe(false));

    await act(async () => { await result.current.addBlockedTime({ date: "2026-08-05", start_time: "14:00", end_time: "15:00" }); });

    expect(api.createBlockedTime).toHaveBeenCalledWith({ date: "2026-08-05", start_time: "14:00", end_time: "15:00" });
    expect((api.getSchedule as jest.Mock).mock.calls.length).toBeGreaterThanOrEqual(2);
  });

  it("surfaces a conflict error from blocked-time creation without throwing", async () => {
    (api.getSchedule as jest.Mock).mockResolvedValue({ ok: true, data: { days: [], pending_time_off_count: 0, last_synced_at: "" } });
    (api.createBlockedTime as jest.Mock).mockResolvedValue({ ok: false, error: { code: "SCHEDULE_CONFLICT", safeMessage: "This time conflicts with an assigned job." } });
    const { result } = renderHook(() => useSchedule(new Date("2026-07-31T12:00:00")), { wrapper });
    await waitFor(() => expect(result.current.isLoading).toBe(false));

    await act(async () => { await result.current.addBlockedTime({ date: "2026-07-31", start_time: "11:00", end_time: "12:00" }); });

    expect(result.current.mutationError).toEqual({ code: "SCHEDULE_CONFLICT", safeMessage: "This time conflicts with an assigned job." });
  });
});
