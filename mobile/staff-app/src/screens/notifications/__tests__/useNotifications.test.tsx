import React from "react";
import { renderHook, act, waitFor } from "@testing-library/react-native";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { useNotifications } from "../useNotifications";

jest.mock("../../../services/notifications/notificationsApi");
import * as api from "../../../services/notifications/notificationsApi";

jest.mock("../../../navigation/session/SessionProvider", () => ({
  useSession: () => ({ accessContext: { authenticated: true, userId: "u1", tenantId: "t1", enabledVerticals: ["home_services"] } }),
}));

function wrapper({ children }: { children: React.ReactNode }) {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return <QueryClientProvider client={client}>{children}</QueryClientProvider>;
}

beforeEach(() => jest.clearAllMocks());

describe("useNotifications (spec sections 2, 7)", () => {
  it("fetches with the given filter/category", async () => {
    (api.getNotifications as jest.Mock).mockResolvedValue({ ok: true, data: { items: [], counts: { all: 0, unread: 0, action_required: 0 }, next_cursor: null } });
    const { result } = renderHook(() => useNotifications("unread", "jobs"), { wrapper });
    await waitFor(() => expect(result.current.isLoading).toBe(false));
    expect(api.getNotifications).toHaveBeenCalledWith("unread", "jobs", expect.anything());
  });

  it("markRead refetches rather than mutating locally (never optimistic)", async () => {
    (api.getNotifications as jest.Mock).mockResolvedValue({ ok: true, data: { items: [], counts: { all: 0, unread: 0, action_required: 0 }, next_cursor: null } });
    (api.markNotificationRead as jest.Mock).mockResolvedValue({ ok: true, data: {} });
    const { result } = renderHook(() => useNotifications("all", null), { wrapper });
    await waitFor(() => expect(result.current.isLoading).toBe(false));

    await act(async () => { await result.current.markRead("n1"); });

    expect(api.markNotificationRead).toHaveBeenCalledWith("n1");
    expect((api.getNotifications as jest.Mock).mock.calls.length).toBeGreaterThanOrEqual(2);
  });

  it("guards against a duplicate mark-all-read while one is in flight", async () => {
    (api.getNotifications as jest.Mock).mockResolvedValue({ ok: true, data: { items: [], counts: { all: 0, unread: 0, action_required: 0 }, next_cursor: null } });
    let resolveMarkAll: (v: any) => void = () => {};
    (api.markAllNotificationsRead as jest.Mock).mockReturnValue(new Promise(res => { resolveMarkAll = res; }));
    const { result } = renderHook(() => useNotifications("all", null), { wrapper });
    await waitFor(() => expect(result.current.isLoading).toBe(false));

    act(() => { result.current.markAllRead(); });
    act(() => { result.current.markAllRead(); });

    expect(api.markAllNotificationsRead).toHaveBeenCalledTimes(1);
    await act(async () => { resolveMarkAll({ ok: true, data: {} }); });
  });
});
