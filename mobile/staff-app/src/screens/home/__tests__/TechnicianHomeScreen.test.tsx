import React from "react";
import { render, screen, waitFor, fireEvent } from "@testing-library/react-native";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { ThemeProvider } from "../../../design-system/themes";
import { TechnicianHomeScreen } from "../TechnicianHomeScreen";
import { MobileHomeDTO } from "../../../services/home/types";

jest.mock("../../../services/home/homeApi");
jest.mock("../../../hooks/useNetworkStatus", () => ({ useNetworkStatus: jest.fn(() => ({ meta: { readiness: "production_ready" }, networkState: "online", cacheState: "fresh", pendingDrafts: 0, syncState: "idle" })) }));
jest.mock("../../../navigation/session/SessionProvider", () => ({
  useSession: () => ({ accessContext: { tenantId: "t1", technicianId: "tech1" } }),
}));

const mockNavigate = jest.fn();
const mockGetParent = jest.fn(() => ({ navigate: mockNavigate }));
jest.mock("@react-navigation/native", () => ({
  ...jest.requireActual("@react-navigation/native"),
  useNavigation: () => ({ navigate: mockNavigate, getParent: mockGetParent }),
}));

import * as homeApi from "../../../services/home/homeApi";
import { useNetworkStatus } from "../../../hooks/useNetworkStatus";

const BASE_HOME: MobileHomeDTO = {
  technician: { id: "tech1", display_name: "Aman", status: "active" },
  availability: { state: "available", updated_at: null },
  shift_summary: { jobs_today: 4, completed: 1, remaining: 3 },
  current_job: {
    job_id: "j1", job_reference: "HS-1044", offering_id: "off1", service_label: "AC Repair",
    job_type_id: "jt1", job_type_label: "Repair", workflow_status: "inspection_started",
    scheduled_date: "2026-07-31", scheduled_time_window: "12:30 PM", locality_label: "Model Town, Ludhiana",
    customer_alias: "Customer C-1044",
    next_required_action: { key: "start_inspection", label: "Continue inspection", allowed: true },
    blocker: null, entity_version: null, workflow_version: null,
  },
  today_schedule: [
    { job_id: "j1", job_reference: "HS-1044", job_type_id: "jt1", workflow_status: "inspection_started", scheduled_time_window: "12:30 PM", locality_label: "Model Town" },
    { job_id: "j2", job_reference: "HS-1050", job_type_id: "jt2", workflow_status: "scheduled", scheduled_time_window: "3:00 PM", locality_label: "Dugri" },
  ],
  action_required: [
    { key: "estimate_awaiting_submission", label: "Estimate awaiting submission", job_id: "j1", job_reference: "HS-1044" },
  ],
  unread_notification_count: 4,
  server_timestamp: "2026-07-31T07:00:00Z",
};

function renderScreen() {
  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <QueryClientProvider client={queryClient}>
      <ThemeProvider>
        <TechnicianHomeScreen />
      </ThemeProvider>
    </QueryClientProvider>,
  );
}

beforeEach(() => {
  jest.clearAllMocks();
  (useNetworkStatus as jest.Mock).mockReturnValue({ meta: { readiness: "production_ready" }, networkState: "online", cacheState: "fresh", pendingDrafts: 0, syncState: "idle" });
});

describe("TechnicianHomeScreen — loaded state (spec sections 2, 15)", () => {
  it("renders the greeting, shift summary, current job, schedule and action-required sections", async () => {
    (homeApi.getMobileHome as jest.Mock).mockResolvedValue({ ok: true, data: BASE_HOME, meta: {} });
    renderScreen();

    await waitFor(() => expect(screen.getByText(/Aman/)).toBeTruthy());
    expect(screen.getByText("HS-1044 · AC Repair")).toBeTruthy();
    expect(screen.getByText("Continue inspection")).toBeTruthy();
    expect(screen.getByText("4")).toBeTruthy(); // jobs today
    expect(screen.getByText("HS-1050")).toBeTruthy(); // schedule row
    expect(screen.getByText("Estimate awaiting submission")).toBeTruthy();
  });

  it("shows the notification bell with an accessible unread-count label", async () => {
    (homeApi.getMobileHome as jest.Mock).mockResolvedValue({ ok: true, data: BASE_HOME, meta: {} });
    renderScreen();
    await waitFor(() => expect(screen.getByLabelText("Notifications, 4 unread")).toBeTruthy());
  });

  it("navigates to the Notifications tab when the bell is pressed", async () => {
    (homeApi.getMobileHome as jest.Mock).mockResolvedValue({ ok: true, data: BASE_HOME, meta: {} });
    renderScreen();
    await waitFor(() => screen.getByLabelText("Notifications, 4 unread"));
    fireEvent.press(screen.getByLabelText("Notifications, 4 unread"));
    expect(mockNavigate).toHaveBeenCalledWith("Notifications");
  });

  it("routes the current job's primary action to the exact guarded execution screen", async () => {
    (homeApi.getMobileHome as jest.Mock).mockResolvedValue({ ok: true, data: BASE_HOME, meta: {} });
    renderScreen();
    await waitFor(() => screen.getByText("Continue inspection"));
    fireEvent.press(screen.getByText("Continue inspection"));
    expect(mockNavigate).toHaveBeenCalledWith("JobExecutionStack", {
      screen: "Inspection", params: { jobId: "j1", jobReference: "HS-1044", targetAction: "start_inspection" },
    });
  });

  it("never exposes an internal blocker code to the technician", async () => {
    (homeApi.getMobileHome as jest.Mock).mockResolvedValue({
      ok: true,
      data: {
        ...BASE_HOME,
        current_job: {
          ...BASE_HOME.current_job!,
          blocker: { code: "ESTIMATE_REQUIRED", message: null },
        },
      },
      meta: {},
    });
    renderScreen();

    await waitFor(() => expect(screen.getByText("Before work can start")).toBeTruthy());
    expect(screen.getByText("Create and send an estimate before starting work.")).toBeTruthy();
    expect(screen.queryByText("ESTIMATE_REQUIRED")).toBeNull();
  });

  it("routes a schedule row tap to Job Detail with only stable IDs, never a full job object", async () => {
    (homeApi.getMobileHome as jest.Mock).mockResolvedValue({ ok: true, data: BASE_HOME, meta: {} });
    renderScreen();
    await waitFor(() => screen.getByText("HS-1050"));
    fireEvent.press(screen.getByText("HS-1050"));
    expect(mockNavigate).toHaveBeenCalledWith("JobExecutionStack", {
      screen: "JobDetail", params: { jobId: "j2", jobReference: "HS-1050", targetAction: undefined },
    });
  });
});

describe("TechnicianHomeScreen — no current job", () => {
  it("shows the compact empty state with only genuine actions", async () => {
    (homeApi.getMobileHome as jest.Mock).mockResolvedValue({ ok: true, data: { ...BASE_HOME, current_job: null }, meta: {} });
    renderScreen();
    await waitFor(() => expect(screen.getByText("You have no active job right now.")).toBeTruthy());
    expect(screen.getByText("View today's jobs")).toBeTruthy();
    expect(screen.queryByText("Find jobs")).toBeNull();
  });
});

describe("TechnicianHomeScreen — empty day", () => {
  it("shows a no-jobs-today message instead of an empty list", async () => {
    (homeApi.getMobileHome as jest.Mock).mockResolvedValue({
      ok: true, data: { ...BASE_HOME, current_job: null, today_schedule: [], action_required: [] }, meta: {},
    });
    renderScreen();
    await waitFor(() => expect(screen.getByText("No jobs scheduled today.")).toBeTruthy());
    expect(screen.getByText("Nothing needs your attention right now.")).toBeTruthy();
  });
});

describe("TechnicianHomeScreen — error/offline", () => {
  it("shows a retryable error state when the projection fails with no cached data", async () => {
    (homeApi.getMobileHome as jest.Mock).mockResolvedValue({
      ok: false, error: { code: "SERVER_UNAVAILABLE", category: "server", safeMessage: "Something went wrong on our end.", retryable: true },
    });
    renderScreen();
    await waitFor(() => expect(screen.getByText("Couldn't load your Home screen")).toBeTruthy());
    expect(screen.getByText("Retry")).toBeTruthy();
  });

  it("shows the offline banner and disables the availability selector while offline", async () => {
    (useNetworkStatus as jest.Mock).mockReturnValue({ meta: { readiness: "production_ready" }, networkState: "offline", cacheState: "fresh", pendingDrafts: 0, syncState: "idle" });
    (homeApi.getMobileHome as jest.Mock).mockResolvedValue({ ok: true, data: BASE_HOME, meta: {} });
    renderScreen();
    await waitFor(() => expect(screen.getByText(/offline/i)).toBeTruthy());
    const availabilityButton = screen.getByLabelText("Availability: Available");
    expect(availabilityButton.props.accessibilityState?.disabled ?? availabilityButton.props.disabled).toBeTruthy();
  });
});

describe("TechnicianHomeScreen — availability update", () => {
  it("optimistically updates and confirms the availability state on success", async () => {
    (homeApi.getMobileHome as jest.Mock).mockResolvedValue({ ok: true, data: BASE_HOME, meta: {} });
    (homeApi.updateAvailability as jest.Mock).mockResolvedValue({ ok: true, data: { state: "busy", updated_at: "2026-07-31T08:00:00Z" }, meta: {} });
    renderScreen();
    await waitFor(() => screen.getByLabelText("Availability: Available"));
    fireEvent.press(screen.getByLabelText("Availability: Available"));
    fireEvent.press((await screen.findAllByText("Busy"))[0]);
    await waitFor(() => expect(homeApi.updateAvailability).toHaveBeenCalledWith("busy"));
  });

  it("rolls back to the previous state and shows a safe message when the update fails", async () => {
    (homeApi.getMobileHome as jest.Mock).mockResolvedValue({ ok: true, data: BASE_HOME, meta: {} });
    (homeApi.updateAvailability as jest.Mock).mockResolvedValue({
      ok: false, error: { code: "SERVER_UNAVAILABLE", category: "server", safeMessage: "Couldn't update your availability. Please try again.", retryable: true },
    });
    renderScreen();
    await waitFor(() => screen.getByLabelText("Availability: Available"));
    fireEvent.press(screen.getByLabelText("Availability: Available"));
    fireEvent.press((await screen.findAllByText("Offline"))[0]);
    await waitFor(() => expect(screen.getByText("Couldn't update your availability. Please try again.")).toBeTruthy());
    expect(screen.getByLabelText("Availability: Available")).toBeTruthy();
  });
});
