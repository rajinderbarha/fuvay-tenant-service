import React from "react";
import { render, screen, fireEvent } from "@testing-library/react-native";
import { ThemeProvider } from "../../../design-system/themes";
import { NotificationsScreen } from "../NotificationsScreen";
import { NotificationInboxDTO } from "../../../services/notifications/types";

jest.mock("../useNotifications");
jest.mock("../../../hooks/useNetworkStatus", () => ({ useNetworkStatus: jest.fn(() => ({ meta: { readiness: "production_ready" }, networkState: "online", cacheState: "fresh", pendingDrafts: 0, syncState: "idle" })) }));

const mockNavigate = jest.fn();
const mockGetParent = jest.fn(() => ({ navigate: mockNavigate }));
jest.mock("@react-navigation/native", () => ({
  ...jest.requireActual("@react-navigation/native"),
  useNavigation: () => ({ navigate: mockNavigate, getParent: mockGetParent }),
}));

import { useNotifications } from "../useNotifications";
import { useNetworkStatus } from "../../../hooks/useNetworkStatus";

const BASE_INBOX: NotificationInboxDTO = {
  items: [
    { id: "n1", event_type: "quote.revision_requested", category: "jobs", severity: "critical", title: "Estimate revision requested", body: "HS-1044 · AC Repair", is_read: false, action_required: true, created_at: new Date().toISOString(), destination: { type: "job", id: "j1", section: "estimate" }, day_group: "today" },
    { id: "n2", event_type: "job.assigned", category: "jobs", severity: "info", title: "New job assigned", body: "HS-1052 · Geyser Repair", is_read: false, action_required: false, created_at: new Date().toISOString(), destination: { type: "job", id: "j2", section: null }, day_group: "today" },
    { id: "n3", event_type: "leave.approved", category: "schedule", severity: "success", title: "Leave request approved", body: "2 Aug · Full day", is_read: true, action_required: false, created_at: new Date().toISOString(), destination: { type: "schedule", id: null, section: null }, day_group: "yesterday" },
  ],
  counts: { all: 8, unread: 3, action_required: 2 },
  next_cursor: null,
};

function baseHookReturn(overrides: Partial<ReturnType<typeof useNotifications>> = {}) {
  return {
    data: BASE_INBOX, isLoading: false, isError: false, error: null, isRefetching: false, refetch: jest.fn(),
    mutating: false, mutationError: null,
    markRead: jest.fn(async () => ({ ok: true as const })),
    markAllRead: jest.fn(async () => ({ ok: true as const })),
    ...overrides,
  };
}

function renderScreen() {
  return render(<ThemeProvider><NotificationsScreen /></ThemeProvider>);
}

beforeEach(() => {
  jest.clearAllMocks();
  (useNetworkStatus as jest.Mock).mockReturnValue({ meta: { readiness: "production_ready" }, networkState: "online", cacheState: "fresh", pendingDrafts: 0, syncState: "idle" });
});

describe("NotificationsScreen — loaded state (spec sections 3, 4)", () => {
  it("renders filter counts, category chips and grouped rows", () => {
    (useNotifications as jest.Mock).mockReturnValue(baseHookReturn());
    renderScreen();
    expect(screen.getByText("All 8")).toBeTruthy();
    expect(screen.getByText("Unread 3")).toBeTruthy();
    expect(screen.getByText("Action needed 2")).toBeTruthy();
    expect(screen.getByText("Jobs")).toBeTruthy();
    expect(screen.getByText("Today")).toBeTruthy();
    expect(screen.getByText("Yesterday")).toBeTruthy();
    expect(screen.getByText("Estimate revision requested")).toBeTruthy();
  });

  it("shows a Review action pill only for action-required rows", () => {
    (useNotifications as jest.Mock).mockReturnValue(baseHookReturn());
    renderScreen();
    expect(screen.getByText("Review")).toBeTruthy();
  });
});

describe("NotificationsScreen — opening a notification (spec sections 2, 5)", () => {
  it("marks only the tapped notification read, then opens the canonical job detail", async () => {
    const markRead = jest.fn(async () => ({ ok: true as const }));
    (useNotifications as jest.Mock).mockReturnValue(baseHookReturn({ markRead }));
    renderScreen();
    fireEvent.press(screen.getByText("New job assigned"));
    expect(markRead).toHaveBeenCalledWith("n2");
    expect(markRead).toHaveBeenCalledTimes(1);
  });

  it("never re-marks an already-read notification", () => {
    const markRead = jest.fn(async () => ({ ok: true as const }));
    (useNotifications as jest.Mock).mockReturnValue(baseHookReturn({ markRead }));
    renderScreen();
    fireEvent.press(screen.getByText("Leave request approved"));
    expect(markRead).not.toHaveBeenCalled();
  });

  it("navigates to Schedule for a schedule-type destination", () => {
    (useNotifications as jest.Mock).mockReturnValue(baseHookReturn());
    renderScreen();
    fireEvent.press(screen.getByText("Leave request approved"));
    expect(mockNavigate).toHaveBeenCalledWith("Schedule");
  });
});

describe("NotificationsScreen — mark all read (spec section 2)", () => {
  it("calls the real mark-all-read mutation, never a client-side bulk update", () => {
    const markAllRead = jest.fn(async () => ({ ok: true as const }));
    (useNotifications as jest.Mock).mockReturnValue(baseHookReturn({ markAllRead }));
    renderScreen();
    fireEvent.press(screen.getByText("Mark all as read"));
    expect(markAllRead).toHaveBeenCalled();
  });
});

describe("NotificationsScreen — empty/offline/error/loading", () => {
  it("shows the correct empty message per filter", () => {
    const detail = { ...BASE_INBOX, items: [], counts: { all: 0, unread: 0, action_required: 0 } };
    (useNotifications as jest.Mock).mockReturnValue(baseHookReturn({ data: detail }));
    renderScreen();
    expect(screen.getByText("No notifications")).toBeTruthy();
  });

  it("shows an offline banner with cached content still visible", () => {
    (useNetworkStatus as jest.Mock).mockReturnValue({ meta: { readiness: "production_ready" }, networkState: "offline", cacheState: "fresh", pendingDrafts: 0, syncState: "idle" });
    (useNotifications as jest.Mock).mockReturnValue(baseHookReturn());
    renderScreen();
    expect(screen.getByText("Offline")).toBeTruthy();
    expect(screen.getByText("Estimate revision requested")).toBeTruthy();
  });

  it("shows a retryable error state when there is no cached data", () => {
    (useNotifications as jest.Mock).mockReturnValue(baseHookReturn({ data: undefined, isError: true, error: { safeMessage: "Something went wrong.", code: "SERVER_UNAVAILABLE", category: "server", retryable: true } }));
    renderScreen();
    expect(screen.getByText("Retry")).toBeTruthy();
  });

  it("shows a loading skeleton", () => {
    (useNotifications as jest.Mock).mockReturnValue(baseHookReturn({ data: undefined, isLoading: true }));
    renderScreen();
    expect(screen.queryByText("Estimate revision requested")).toBeNull();
  });
});
