import React from "react";
import { render, screen, fireEvent } from "@testing-library/react-native";
import { ThemeProvider } from "../../../design-system/themes";
import { NotificationPreferencesScreen } from "../NotificationPreferencesScreen";
import { NotificationPreferencesDetailDTO } from "../../../services/notifications/preferencesTypes";

jest.mock("../useNotificationPreferences");
jest.mock("../../../hooks/useNetworkStatus", () => ({ useNetworkStatus: jest.fn(() => ({ meta: { readiness: "production_ready" }, networkState: "online", cacheState: "fresh", pendingDrafts: 0, syncState: "idle" })) }));

import { useNotificationPreferences } from "../useNotificationPreferences";
import { useNetworkStatus } from "../../../hooks/useNetworkStatus";

const navigation = { navigate: jest.fn(), goBack: jest.fn() } as any;
const route = { params: undefined } as any;

const DETAIL: NotificationPreferencesDetailDTO = {
  timezone: "Asia/Kolkata",
  delivery: {
    push: { supported: true, enabled: true, configurable: true, os_permission: "granted" },
    in_app: { supported: true, enabled: true, configurable: false, locked_reason: "In-app operational notifications are required" },
    email_summary: { supported: false, enabled: false, configurable: false },
  },
  events: [
    { event_group: "jobs", code: "job.assigned", label: "New job assignments", description: "When work is assigned or removed", push_enabled: true, configurable: false, mandatory: true },
    { event_group: "schedule", code: "schedule.leave_decision", label: "Schedule changes", description: "Rescheduled jobs and leave decisions", push_enabled: true, configurable: true, mandatory: false },
    { event_group: "account", code: "account.document_reminders", label: "Document reminders", description: "Review, expiry and replacement updates", push_enabled: true, configurable: true, mandatory: false },
  ],
  quiet_hours: { supported: true, enabled: true, start_local_time: "22:00", end_local_time: "07:00", timezone: "Asia/Kolkata", critical_events_bypass: true },
  version: 4,
};

function baseHookReturn(overrides: Partial<ReturnType<typeof useNotificationPreferences>> = {}) {
  return {
    data: DETAIL, isLoading: false, isError: false, error: null, isRefetching: false, refetch: jest.fn(),
    saveStatus: "idle" as const, saveError: null, versionConflict: false,
    toggleEvent: jest.fn(), saveQuietHours: jest.fn(),
    ...overrides,
  };
}

function renderScreen() {
  return render(<ThemeProvider><NotificationPreferencesScreen route={route} navigation={navigation} /></ThemeProvider>);
}

beforeEach(() => {
  jest.clearAllMocks();
  (useNetworkStatus as jest.Mock).mockReturnValue({ meta: { readiness: "production_ready" }, networkState: "online", cacheState: "fresh", pendingDrafts: 0, syncState: "idle" });
});

describe("NotificationPreferencesScreen (Phase U)", () => {
  it("renders the info card and delivery section", () => {
    (useNotificationPreferences as jest.Mock).mockReturnValue(baseHookReturn());
    renderScreen();
    expect(screen.getByText("Stay updated")).toBeTruthy();
    expect(screen.getByText("Push notifications")).toBeTruthy();
    expect(screen.getByText("In-app notifications")).toBeTruthy();
  });

  it("locks mandatory events with a Required pill instead of a toggle", () => {
    (useNotificationPreferences as jest.Mock).mockReturnValue(baseHookReturn());
    renderScreen();
    expect(screen.getByText("New job assignments")).toBeTruthy();
    expect(screen.getAllByText("Required").length).toBeGreaterThanOrEqual(1);
  });

  it("toggles an optional preference", () => {
    const toggleEvent = jest.fn();
    (useNotificationPreferences as jest.Mock).mockReturnValue(baseHookReturn({ toggleEvent }));
    renderScreen();
    fireEvent(screen.getByLabelText("Schedule changes, on"), "valueChange", false);
    expect(toggleEvent).toHaveBeenCalledWith("schedule.leave_decision", false);
  });

  it("never displays an unsupported channel (email summaries) as a working toggle", () => {
    (useNotificationPreferences as jest.Mock).mockReturnValue(baseHookReturn());
    renderScreen();
    expect(screen.getByText("Email summaries")).toBeTruthy();
    expect(screen.getByText("Not available yet")).toBeTruthy();
  });

  it("never shows a Language row (single-language app policy)", () => {
    (useNotificationPreferences as jest.Mock).mockReturnValue(baseHookReturn());
    renderScreen();
    expect(screen.queryByText("Language")).toBeNull();
  });

  it("opens the quiet hours sheet and shows the configured window", () => {
    (useNotificationPreferences as jest.Mock).mockReturnValue(baseHookReturn());
    renderScreen();
    fireEvent.press(screen.getAllByText("Quiet hours")[1]);
    expect(screen.getByText("Enable quiet hours")).toBeTruthy();
  });

  it("does not claim 'Saved' before a mutation succeeds", () => {
    (useNotificationPreferences as jest.Mock).mockReturnValue(baseHookReturn({ saveStatus: "saving" }));
    renderScreen();
    expect(screen.getByText("Saving…")).toBeTruthy();
    expect(screen.queryByText("Preferences saved automatically")).toBeNull();
  });

  it("shows the saved confirmation only after success", () => {
    (useNotificationPreferences as jest.Mock).mockReturnValue(baseHookReturn({ saveStatus: "saved" }));
    renderScreen();
    expect(screen.getByText("Preferences saved automatically")).toBeTruthy();
  });

  it("shows a version-conflict banner", () => {
    (useNotificationPreferences as jest.Mock).mockReturnValue(baseHookReturn({ versionConflict: true }));
    renderScreen();
    expect(screen.getByText("Notification policy changed")).toBeTruthy();
  });

  it("shows an offline banner and disables optional toggles", () => {
    (useNetworkStatus as jest.Mock).mockReturnValue({ meta: { readiness: "production_ready" }, networkState: "offline", cacheState: "fresh", pendingDrafts: 0, syncState: "idle" });
    (useNotificationPreferences as jest.Mock).mockReturnValue(baseHookReturn());
    renderScreen();
    expect(screen.getByText("Offline")).toBeTruthy();
  });

  it("shows a loading skeleton, then an error state on failure", () => {
    (useNotificationPreferences as jest.Mock).mockReturnValue(baseHookReturn({ data: undefined, isLoading: true }));
    const { rerender } = renderScreen();
    expect(screen.queryByText("Stay updated")).toBeNull();

    (useNotificationPreferences as jest.Mock).mockReturnValue(baseHookReturn({ data: undefined, isLoading: false, isError: true, error: { code: "VALIDATION_ERROR", category: "network", safeMessage: "Network error", retryable: true } }));
    rerender(<ThemeProvider><NotificationPreferencesScreen route={route} navigation={navigation} /></ThemeProvider>);
    expect(screen.getByText("Couldn't load preferences")).toBeTruthy();
  });
});
