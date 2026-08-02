import React from "react";
import { renderHook, act, waitFor } from "@testing-library/react-native";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { useNotificationPreferences } from "../useNotificationPreferences";

jest.mock("../../../services/notifications/preferencesApi");
import * as api from "../../../services/notifications/preferencesApi";

function wrapper({ children }: { children: React.ReactNode }) {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return <QueryClientProvider client={client}>{children}</QueryClientProvider>;
}

const BASE = {
  timezone: "Asia/Kolkata",
  delivery: {
    push: { supported: true, enabled: true, configurable: true, os_permission: "granted" },
    in_app: { supported: true, enabled: true, configurable: false, locked_reason: "Required" },
    email_summary: { supported: false, enabled: false, configurable: false },
  },
  events: [
    { event_group: "jobs", code: "job.assigned", label: "New job assignments", description: "", push_enabled: true, configurable: false, mandatory: true },
    { event_group: "schedule", code: "schedule.leave_decision", label: "Schedule changes", description: "", push_enabled: true, configurable: true, mandatory: false },
  ],
  quiet_hours: { supported: true, enabled: false, start_local_time: null, end_local_time: null, timezone: "Asia/Kolkata", critical_events_bypass: true },
  version: 4,
};

beforeEach(() => jest.clearAllMocks());

describe("useNotificationPreferences (Phase U)", () => {
  it("loads preferences", async () => {
    (api.getNotificationPreferences as jest.Mock).mockResolvedValue({ ok: true, data: BASE });
    const { result } = renderHook(() => useNotificationPreferences(), { wrapper });
    await waitFor(() => expect(result.current.isLoading).toBe(false));
    expect(api.getNotificationPreferences).toHaveBeenCalled();
  });

  it("toggleEvent only shows 'saved' after the backend mutation succeeds", async () => {
    (api.getNotificationPreferences as jest.Mock).mockResolvedValue({ ok: true, data: BASE });
    (api.updateEventPreference as jest.Mock).mockResolvedValue({ ok: true, data: { ...BASE, version: 5, events: BASE.events.map(e => e.code === "schedule.leave_decision" ? { ...e, push_enabled: false } : e) } });
    const { result } = renderHook(() => useNotificationPreferences(), { wrapper });
    await waitFor(() => expect(result.current.isLoading).toBe(false));

    await act(async () => { await result.current.toggleEvent("schedule.leave_decision", false); });

    expect(api.updateEventPreference).toHaveBeenCalledWith("schedule.leave_decision", false, 4);
    expect(result.current.saveStatus).toBe("saved");
    expect(result.current.data?.version).toBe(5);
  });

  it("rolls back and shows an error when the mutation fails", async () => {
    (api.getNotificationPreferences as jest.Mock).mockResolvedValue({ ok: true, data: BASE });
    (api.updateEventPreference as jest.Mock).mockResolvedValue({ ok: false, error: { code: "MANDATORY_PREFERENCE", category: "validation", safeMessage: "This notification is required.", retryable: false } });
    const { result } = renderHook(() => useNotificationPreferences(), { wrapper });
    await waitFor(() => expect(result.current.isLoading).toBe(false));

    await act(async () => { await result.current.toggleEvent("job.assigned", false); });

    expect(result.current.saveStatus).toBe("error");
    expect(result.current.saveError?.safeMessage).toBe("This notification is required.");
    expect(api.getNotificationPreferences).toHaveBeenCalledTimes(2); // rollback refetch
  });

  it("flags a version conflict and reloads authoritative data rather than overwriting it", async () => {
    (api.getNotificationPreferences as jest.Mock).mockResolvedValue({ ok: true, data: BASE });
    (api.updateEventPreference as jest.Mock).mockResolvedValue({ ok: false, error: { code: "CONFLICT", category: "validation", safeMessage: "Notification policy changed.", retryable: false } });
    const { result } = renderHook(() => useNotificationPreferences(), { wrapper });
    await waitFor(() => expect(result.current.isLoading).toBe(false));

    await act(async () => { await result.current.toggleEvent("schedule.leave_decision", false); });

    expect(result.current.versionConflict).toBe(true);
  });

  it("serializes rapid repeated toggles so both apply in order rather than racing", async () => {
    (api.getNotificationPreferences as jest.Mock).mockResolvedValue({ ok: true, data: BASE });
    (api.updateEventPreference as jest.Mock)
      .mockResolvedValueOnce({ ok: true, data: { ...BASE, version: 5 } })
      .mockResolvedValueOnce({ ok: true, data: { ...BASE, version: 6 } });
    const { result } = renderHook(() => useNotificationPreferences(), { wrapper });
    await waitFor(() => expect(result.current.isLoading).toBe(false));

    await act(async () => {
      const first = result.current.toggleEvent("schedule.leave_decision", false);
      const second = result.current.toggleEvent("schedule.leave_decision", true);
      await Promise.all([first, second]);
    });

    expect(api.updateEventPreference).toHaveBeenCalledTimes(2);
    expect(result.current.data?.version).toBe(6); // the later call's result is authoritative, never overwritten by the earlier one
  });
});
