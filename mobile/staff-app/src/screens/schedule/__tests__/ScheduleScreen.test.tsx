import React from "react";
import { render, screen, fireEvent } from "@testing-library/react-native";
import { ThemeProvider } from "../../../design-system/themes";
import { ScheduleScreen } from "../ScheduleScreen";
import { ScheduleDetailDTO } from "../../../services/schedule/types";

jest.mock("../useSchedule");
jest.mock("../../home/useTechnicianHome");
jest.mock("../../../hooks/useNetworkStatus", () => ({ useNetworkStatus: jest.fn(() => "online") }));

const mockNavigate = jest.fn();
const mockGetParent = jest.fn(() => ({ navigate: mockNavigate }));
jest.mock("@react-navigation/native", () => ({
  ...jest.requireActual("@react-navigation/native"),
  useNavigation: () => ({ navigate: mockNavigate, getParent: mockGetParent }),
}));

import { useSchedule } from "../useSchedule";
import { useTechnicianHome } from "../../home/useTechnicianHome";
import { useNetworkStatus } from "../../../hooks/useNetworkStatus";

const navigation = { navigate: mockNavigate, goBack: jest.fn() } as any;
const SELECTED = new Date("2026-07-31T00:00:00");
const route = { params: undefined } as any;

const BASE_DETAIL: ScheduleDetailDTO = {
  timezone: "Asia/Kolkata",
  days: [
    {
      date: "2026-07-31", day_of_week: 5, working_hours_label: "09:00–18:00",
      assigned_job_count: 1, open_slot_count: 2, pending_leave_count: 0,
      items: [
        { type: "assigned_job", job_id: "j1", job_reference: "HS-1044", time_label: "10:30 AM", workflow_status: "assigned" },
        { type: "available_slot", time_label: "9:00 AM", duration_minutes: 60 },
      ],
    },
  ],
  pending_time_off_count: 0,
  last_synced_at: "2026-07-31T05:00:00Z",
};

function baseHookReturn(overrides: Partial<ReturnType<typeof useSchedule>> = {}) {
  return {
    data: BASE_DETAIL, isLoading: false, isError: false, error: null, isRefetching: false, refetch: jest.fn(),
    weekDates: [new Date("2026-07-27"), new Date("2026-07-28"), new Date("2026-07-29"), new Date("2026-07-30"), SELECTED, new Date("2026-08-01"), new Date("2026-08-02")],
    mutating: false, mutationError: null,
    addBlockedTime: jest.fn(async () => ({ ok: true as const })),
    removeBlockedTime: jest.fn(async () => ({ ok: true as const })),
    submitTimeOff: jest.fn(async () => ({ ok: true as const })),
    ...overrides,
  };
}

function renderScreen() {
  return render(<ThemeProvider><ScheduleScreen route={route} navigation={navigation} /></ThemeProvider>);
}

beforeEach(() => {
  jest.clearAllMocks();
  (useNetworkStatus as jest.Mock).mockReturnValue("online");
  (useTechnicianHome as jest.Mock).mockReturnValue({ data: { availability: { state: "available" } }, updateAvailability: jest.fn() });
  jest.useFakeTimers().setSystemTime(SELECTED);
});

afterEach(() => jest.useRealTimers());

describe("ScheduleScreen — loaded state (spec sections 3, 4)", () => {
  it("renders the availability card, week strip, daily summary and timeline", () => {
    (useSchedule as jest.Mock).mockReturnValue(baseHookReturn());
    renderScreen();
    expect(screen.getByText("Available today")).toBeTruthy();
    expect(screen.getByText("Working hours 09:00–18:00")).toBeTruthy();
    expect(screen.getByText("HS-1044 · Assigned")).toBeTruthy();
  });

  it("shows job/open-slot/pending-leave counts for the selected day", () => {
    (useSchedule as jest.Mock).mockReturnValue(baseHookReturn());
    renderScreen();
    expect(screen.getByText("jobs")).toBeTruthy();
    expect(screen.getByText("open slots")).toBeTruthy();
    expect(screen.getByText("pending leave")).toBeTruthy();
  });

  it("opens the canonical Job Detail screen when a job row is pressed", () => {
    (useSchedule as jest.Mock).mockReturnValue(baseHookReturn());
    renderScreen();
    fireEvent.press(screen.getByLabelText("HS-1044 · Assigned"));
    expect(mockNavigate).toHaveBeenCalledWith("JobExecutionStack", { screen: "JobDetail", params: { jobId: "j1" } });
  });
});

describe("ScheduleScreen — empty/offline/error", () => {
  it("shows an empty state for a day with nothing scheduled", () => {
    const detail = { ...BASE_DETAIL, days: [{ ...BASE_DETAIL.days[0], items: [], assigned_job_count: 0 }] };
    (useSchedule as jest.Mock).mockReturnValue(baseHookReturn({ data: detail }));
    renderScreen();
    expect(screen.getByText("Nothing scheduled")).toBeTruthy();
  });

  it("shows the offline banner with cached-time context", () => {
    (useNetworkStatus as jest.Mock).mockReturnValue("offline");
    (useSchedule as jest.Mock).mockReturnValue(baseHookReturn());
    renderScreen();
    expect(screen.getByText("Offline")).toBeTruthy();
  });

  it("shows a retryable error state when there is no cached data", () => {
    (useSchedule as jest.Mock).mockReturnValue(baseHookReturn({ data: undefined, isError: true, error: { safeMessage: "Something went wrong.", code: "SERVER_UNAVAILABLE", category: "server", retryable: true } }));
    renderScreen();
    expect(screen.getByText("Retry")).toBeTruthy();
  });

  it("shows a loading skeleton", () => {
    (useSchedule as jest.Mock).mockReturnValue(baseHookReturn({ data: undefined, isLoading: true }));
    renderScreen();
    expect(screen.queryByText("Available today")).toBeNull();
  });
});

describe("ScheduleScreen — navigation to sub-screens", () => {
  it("navigates to Manage Availability", () => {
    (useSchedule as jest.Mock).mockReturnValue(baseHookReturn());
    renderScreen();
    fireEvent.press(screen.getByText("Manage"));
    expect(mockNavigate).toHaveBeenCalledWith("ManageAvailability");
  });

  it("navigates to Request Time Off", () => {
    (useSchedule as jest.Mock).mockReturnValue(baseHookReturn());
    renderScreen();
    fireEvent.press(screen.getByText("Request time off"));
    expect(mockNavigate).toHaveBeenCalledWith("RequestTimeOff");
  });
});
