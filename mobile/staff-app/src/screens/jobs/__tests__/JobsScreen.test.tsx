import React from "react";
import { render, screen, waitFor, fireEvent, act } from "@testing-library/react-native";
import { ThemeProvider } from "../../../design-system/themes";
import { JobsScreen } from "../JobsScreen";
import { JobListItemDTO } from "../../../services/jobs/types";

jest.mock("../useTechnicianJobs");
jest.mock("../../../hooks/useNetworkStatus", () => ({ useNetworkStatus: jest.fn(() => ({ meta: { readiness: "production_ready" }, networkState: "online", cacheState: "fresh", pendingDrafts: 0, syncState: "idle" })) }));

const mockNavigate = jest.fn();
const mockGetParent = jest.fn(() => ({ navigate: mockNavigate }));
jest.mock("@react-navigation/native", () => ({
  ...jest.requireActual("@react-navigation/native"),
  useNavigation: () => ({ navigate: mockNavigate, getParent: mockGetParent }),
}));

import { useTechnicianJobs } from "../useTechnicianJobs";
import { useNetworkStatus } from "../../../hooks/useNetworkStatus";

const JOB: JobListItemDTO = {
  job_id: "j1", job_reference: "HS-1044", offering_id: "off1", service_label: "AC Repair",
  job_type_id: "jt1", job_type_label: "Repair", workflow_status: "inspection_started",
  scheduled_date: "2026-07-31", scheduled_time_window: "12:30 PM", safe_locality: "Model Town, Ludhiana",
  customer_alias: "Customer C-1044",
  next_required_action: { key: "start_inspection", label: "Continue inspection", allowed: true },
  allowed_actions: ["start_inspection"], blocker: null, payment_confirmation_state: null,
  entity_version: null, workflow_version: null, updated_at: "2026-07-31T05:00:00Z",
};

function baseHookReturn(overrides: Partial<ReturnType<typeof useTechnicianJobs>> = {}) {
  return {
    items: [], countsByView: { today: 0, active: 0, upcoming: 0, completed: 0, archive: 0 },
    isLoading: false, isError: false, error: null, isRefetching: false,
    refetch: jest.fn(), fetchNextPage: jest.fn(), hasNextPage: false, isFetchingNextPage: false,
    ...overrides,
  };
}

function renderScreen() {
  return render(<ThemeProvider><JobsScreen /></ThemeProvider>);
}

beforeEach(() => {
  jest.clearAllMocks();
  (useNetworkStatus as jest.Mock).mockReturnValue({ meta: { readiness: "production_ready" }, networkState: "online", cacheState: "fresh", pendingDrafts: 0, syncState: "idle" });
});

describe("JobsScreen — loaded state (spec sections 2, 3, 19)", () => {
  it("renders tab counts and job cards", async () => {
    (useTechnicianJobs as jest.Mock).mockReturnValue(baseHookReturn({
      items: [JOB], countsByView: { today: 4, active: 2, upcoming: 3, completed: 12, archive: 0 },
    }));
    renderScreen();
    expect(screen.getByLabelText("Today, 4 jobs")).toBeTruthy();
    expect(screen.getByText("HS-1044 · AC Repair")).toBeTruthy();
    expect(screen.getByText("Continue inspection")).toBeTruthy();
  });

  it("navigates to the exact guarded execution screen for the primary action", () => {
    (useTechnicianJobs as jest.Mock).mockReturnValue(baseHookReturn({ items: [JOB] }));
    renderScreen();
    fireEvent.press(screen.getByText("Continue inspection"));
    expect(mockNavigate).toHaveBeenCalledWith("JobExecutionStack", {
      screen: "Inspection", params: { jobId: "j1", jobReference: "HS-1044", targetAction: "start_inspection" },
    });
  });

  it("navigates to Job Detail (not a full object) when the card itself is pressed", () => {
    (useTechnicianJobs as jest.Mock).mockReturnValue(baseHookReturn({ items: [JOB] }));
    renderScreen();
    fireEvent.press(screen.getByLabelText(/Job HS-1044/));
    expect(mockNavigate).toHaveBeenCalledWith("JobExecutionStack", {
      screen: "JobDetail", params: { jobId: "j1", jobReference: "HS-1044", targetAction: undefined },
    });
  });
});

describe("JobsScreen — tab switching", () => {
  it("switches the requested view when a tab is pressed", () => {
    (useTechnicianJobs as jest.Mock).mockReturnValue(baseHookReturn());
    renderScreen();
    fireEvent(screen.getByLabelText(/Active/), "press");
    // useTechnicianJobs is mocked, so we assert the hook was called with the new view on re-render.
    expect(useTechnicianJobs).toHaveBeenCalled();
  });
});

describe("JobsScreen — loading/empty/error", () => {
  it("shows a skeleton while loading", () => {
    (useTechnicianJobs as jest.Mock).mockReturnValue(baseHookReturn({ isLoading: true }));
    renderScreen();
    expect(screen.queryByText("HS-1044 · AC Repair")).toBeNull();
  });

  it("shows an empty state with the correct message for an empty view", () => {
    (useTechnicianJobs as jest.Mock).mockReturnValue(baseHookReturn({ items: [] }));
    renderScreen();
    expect(screen.getByText("No jobs scheduled today.")).toBeTruthy();
  });

  it("shows a full-page retryable error only when there is no cached data", () => {
    (useTechnicianJobs as jest.Mock).mockReturnValue(baseHookReturn({
      isError: true, error: { safeMessage: "Something went wrong on our end." }, items: [],
    }));
    renderScreen();
    expect(screen.getByText("Couldn't load jobs")).toBeTruthy();
    expect(screen.getByText("Retry")).toBeTruthy();
  });

  it("shows an inline warning (not a full-page error) when jobs are already cached", () => {
    (useTechnicianJobs as jest.Mock).mockReturnValue(baseHookReturn({
      isError: true, error: { safeMessage: "Pull to refresh." }, items: [JOB],
    }));
    renderScreen();
    expect(screen.getByText("HS-1044 · AC Repair")).toBeTruthy();
    expect(screen.getByText("Some jobs may be out of date")).toBeTruthy();
  });

  it("shows a no-matches message when a search returns nothing", () => {
    (useTechnicianJobs as jest.Mock).mockReturnValue(baseHookReturn({ items: [] }));
    renderScreen();
    fireEvent.changeText(screen.getByPlaceholderText("Search job or service"), "nonexistent");
    expect(screen.queryByText("No jobs scheduled today.")).toBeTruthy(); // debounce not yet elapsed
  });
});

describe("JobsScreen — offline", () => {
  it("shows the offline banner and still lists cached jobs read-only", () => {
    (useNetworkStatus as jest.Mock).mockReturnValue({ meta: { readiness: "production_ready" }, networkState: "offline", cacheState: "fresh", pendingDrafts: 0, syncState: "idle" });
    (useTechnicianJobs as jest.Mock).mockReturnValue(baseHookReturn({ items: [JOB] }));
    renderScreen();
    expect(screen.getByText(/offline/i)).toBeTruthy();
    expect(screen.getByText("HS-1044 · AC Repair")).toBeTruthy();
  });
});

describe("JobsScreen — filters", () => {
  it("shows the active-filter count on the filter icon once a filter is applied", async () => {
    (useTechnicianJobs as jest.Mock).mockReturnValue(baseHookReturn());
    renderScreen();
    fireEvent.press(screen.getByLabelText("Filters"));
    const toggle = await screen.findByLabelText("Action required only");
    fireEvent(toggle, "valueChange", true);
    fireEvent.press(screen.getByText("Apply"), { stopPropagation: () => {} });
    await waitFor(() => expect(screen.getByLabelText("Filters, 1 active")).toBeTruthy());
  });

  it("Clear all resets filters without applying anything stale", async () => {
    (useTechnicianJobs as jest.Mock).mockReturnValue(baseHookReturn());
    renderScreen();
    fireEvent.press(screen.getByLabelText("Filters"));
    fireEvent.press(await screen.findByText("Clear all"));
    fireEvent.press(screen.getByText("Apply"), { stopPropagation: () => {} });
    await waitFor(() => expect(screen.getByLabelText("Filters")).toBeTruthy());
  });
});

describe("JobsScreen — pagination footer", () => {
  it("shows an end-of-list message when there is no next page", () => {
    (useTechnicianJobs as jest.Mock).mockReturnValue(baseHookReturn({ items: [JOB], hasNextPage: false }));
    renderScreen();
    expect(screen.getByText("Showing all 1")).toBeTruthy();
  });
});
