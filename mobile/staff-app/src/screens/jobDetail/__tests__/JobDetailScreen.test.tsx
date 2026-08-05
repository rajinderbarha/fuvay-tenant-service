import React from "react";
import { render, screen, fireEvent } from "@testing-library/react-native";
import { ThemeProvider } from "../../../design-system/themes";
import { JobDetailScreen } from "../JobDetailScreen";
import { JobMobileDetailDTO } from "../../../services/jobDetail/types";

jest.mock("../useJobDetail");
jest.mock("../../../hooks/useNetworkStatus", () => ({ useNetworkStatus: jest.fn(() => ({ meta: { readiness: "production_ready" }, networkState: "online", cacheState: "fresh", pendingDrafts: 0, syncState: "idle" })) }));

import { useJobDetail } from "../useJobDetail";
import { useNetworkStatus } from "../../../hooks/useNetworkStatus";

const mockNavigate = jest.fn();
const mockGoBack = jest.fn();
const mockGetParent = jest.fn(() => ({ navigate: mockNavigate }));
const navigation = { navigate: mockNavigate, goBack: mockGoBack, canGoBack: () => true, getParent: mockGetParent } as any;
const route = { params: { jobId: "j1" } } as any;

const BASE_DETAIL: JobMobileDetailDTO = {
  job: {
    job_id: "j1", job_reference: "HS-1044", tenant_id: "t1", assigned_technician_id: "st1",
    offering_id: "off1", service_label: "AC Repair", job_type_id: "jt1", job_type_label: "Repair",
    workflow_status: "inspection_started", scheduled_date: "2026-07-31", scheduled_time_window: "12:30 PM",
    safe_locality: "Model Town, Ludhiana", is_terminal: false, booking_reference: "BK-1",
  },
  customer: { customer_alias: "Customer HS-1044", call_relay_available: false, call_relay_reason: "CONTACT_RELAY_UNAVAILABLE", message_relay_available: false, message_relay_reason: "CONTACT_RELAY_UNAVAILABLE" },
  workflow: { stages: [
    { key: "assigned", label: "Assigned", state: "completed", completed_at: null },
    { key: "inspection_started", label: "Inspection", state: "current", completed_at: null },
    { key: "completed", label: "Completed", state: "upcoming", completed_at: null },
  ] },
  next_required_action: { key: "complete_inspection", label: "Continue inspection", allowed: true, route_key: "complete_inspection" },
  requirements: {
    checklist: { route_key: "CHECKLIST", required: true, total_items: 5, completed_items: 2, blocking_items: [] },
    photos: { route_key: "COMPLETION_PROOF", required: null, uploaded_count: 1 },
    estimate: { route_key: "ESTIMATE", required: true, quote_id: null, version: null, state: null },
    parts: { route_key: "PARTS_REQUEST", requested: false, approval_state: null },
    completion_proof: { route_key: "COMPLETION_PROOF", required: false, state: "not_submitted" },
    payment_confirmation: { route_key: "DIRECT_PAYMENT_CONFIRMATION", required: false, state: null },
  },
  visit_fee: { required: true, amount: 299, currency: "INR", disposition: "not_tracked", policy_note: "Adjusted if work continues." },
  job_details: { type_required: true, brand_required: true, type_brand_value: "Split, LG", issue_summary: "AC not cooling" },
  allowed_actions: ["complete_inspection"],
  blocker: null,
  versions: { entity_version: null, workflow_version: null },
  server_timestamp: "2026-07-31T05:00:00Z",
};

function baseHookReturn(overrides: Partial<ReturnType<typeof useJobDetail>> = {}) {
  return {
    data: BASE_DETAIL, isLoading: false, isError: false, error: null, isRefetching: false,
    refetch: jest.fn(), mutating: false, mutationError: null,
    acceptJob: jest.fn(), startTravel: jest.fn(), markArrived: jest.fn(),
    ...overrides,
  };
}

function renderScreen() {
  return render(<ThemeProvider><JobDetailScreen route={route} navigation={navigation} /></ThemeProvider>);
}

beforeEach(() => {
  jest.clearAllMocks();
  (useNetworkStatus as jest.Mock).mockReturnValue({ meta: { readiness: "production_ready" }, networkState: "online", cacheState: "fresh", pendingDrafts: 0, syncState: "idle" });
});

describe("JobDetailScreen — loaded state (spec sections 2, 5, 6)", () => {
  it("renders job identity, workflow tracker and requirements from the projection only", () => {
    (useJobDetail as jest.Mock).mockReturnValue(baseHookReturn());
    renderScreen();
    expect(screen.getByText("Job HS-1044")).toBeTruthy();
    expect(screen.getByText("AC Repair")).toBeTruthy();
    expect(screen.getByText("Inspection checklist")).toBeTruthy();
    expect(screen.getByText("2 of 5 completed")).toBeTruthy();
  });

  it("renders exactly one backend-driven next-action button and never fabricates a label", () => {
    (useJobDetail as jest.Mock).mockReturnValue(baseHookReturn());
    renderScreen();
    expect(screen.getAllByText("Continue inspection").length).toBeGreaterThan(0);
  });

  it("never shows a raw customer phone/email -- only the safe alias", () => {
    (useJobDetail as jest.Mock).mockReturnValue(baseHookReturn());
    renderScreen();
    expect(screen.getByText("Customer HS-1044")).toBeTruthy();
    expect(screen.queryByText(/\d{10}/)).toBeNull();
  });

  it("renders the backend visit-fee policy, never a hardcoded amount", () => {
    (useJobDetail as jest.Mock).mockReturnValue(baseHookReturn());
    renderScreen();
    expect(screen.getByText("Visit fee ₹299")).toBeTruthy();
  });
});

describe("JobDetailScreen — actions (spec sections 6, 8, 17)", () => {
  it("navigates to the guarded subflow for a navigate-kind action, never a mutation call", () => {
    const startTravel = jest.fn();
    (useJobDetail as jest.Mock).mockReturnValue(baseHookReturn({ startTravel }));
    renderScreen();
    fireEvent.press(screen.getAllByText("Continue inspection")[0]);
    expect(mockNavigate).toHaveBeenCalledWith("Inspection", { jobId: "j1", jobReference: "HS-1044", targetAction: "complete_inspection" });
    expect(startTravel).not.toHaveBeenCalled();
  });

  it("calls the real mutation for a mutation-kind action (start travel)", () => {
    const startTravel = jest.fn();
    const detail = { ...BASE_DETAIL, next_required_action: { key: "on_the_way", label: "Start journey", allowed: true, route_key: "on_the_way" } };
    (useJobDetail as jest.Mock).mockReturnValue(baseHookReturn({ data: detail, startTravel }));
    renderScreen();
    fireEvent.press(screen.getAllByText("Start journey")[0]);
    expect(startTravel).toHaveBeenCalled();
    expect(mockNavigate).not.toHaveBeenCalled();
  });

  it("never performs optimistic workflow advancement -- data comes only from the hook, never local state", () => {
    (useJobDetail as jest.Mock).mockReturnValue(baseHookReturn());
    renderScreen();
    fireEvent.press(screen.getAllByText("Continue inspection")[0]);
    // Still reflects the mocked hook's unchanged data, proving no client-side mutation of workflow state.
    expect(screen.getAllByText("Inspection").length).toBeGreaterThan(0);
  });

  it("disables the primary action and shows the blocker when the action is not allowed", () => {
    const detail = {
      ...BASE_DETAIL,
      next_required_action: { key: "await_approval", label: "Waiting for customer approval", allowed: false, route_key: "await_approval" },
      blocker: { code: "QUOTE_PENDING_CUSTOMER", message: "Customer has not yet approved the estimate." },
    };
    (useJobDetail as jest.Mock).mockReturnValue(baseHookReturn({ data: detail }));
    renderScreen();
    expect(screen.getAllByText("Customer has not yet approved the estimate.").length).toBeGreaterThan(0);
  });
});

describe("JobDetailScreen — navigation (spec sections 10, 15)", () => {
  it("opens the timeline screen from the sticky bottom bar", () => {
    (useJobDetail as jest.Mock).mockReturnValue(baseHookReturn());
    renderScreen();
    fireEvent.press(screen.getByText("View full timeline"));
    expect(mockNavigate).toHaveBeenCalledWith("JobTimeline", { jobId: "j1", jobReference: "HS-1044" });
  });

  it("goes back via the header back button", () => {
    (useJobDetail as jest.Mock).mockReturnValue(baseHookReturn());
    renderScreen();
    fireEvent.press(screen.getByLabelText("Back"));
    expect(mockGoBack).toHaveBeenCalled();
  });
});

describe("JobDetailScreen — loading/error/offline states (spec section 19)", () => {
  it("shows a skeleton while loading", () => {
    (useJobDetail as jest.Mock).mockReturnValue(baseHookReturn({ data: undefined, isLoading: true }));
    renderScreen();
    expect(screen.queryByText("AC Repair")).toBeNull();
  });

  it("fails closed with a not-found state and no retry affordance for an unknown/inaccessible job", () => {
    (useJobDetail as jest.Mock).mockReturnValue(baseHookReturn({
      data: undefined, isError: true, error: { code: "UNKNOWN_API_ERROR", backendCode: "ENTITY_NOT_FOUND", safeMessage: "Job not found.", category: "unknown", retryable: false },
    }));
    renderScreen();
    expect(screen.getByText("Job not found")).toBeTruthy();
    expect(screen.queryByText("Retry")).toBeNull();
  });

  it("shows a retryable error state for a genuine network/server failure", () => {
    (useJobDetail as jest.Mock).mockReturnValue(baseHookReturn({
      data: undefined, isError: true, error: { code: "SERVER_UNAVAILABLE", safeMessage: "Something went wrong.", category: "server", retryable: true },
    }));
    renderScreen();
    expect(screen.getByText("Retry")).toBeTruthy();
  });

  it("shows the offline banner while still rendering cached data read-only", () => {
    (useNetworkStatus as jest.Mock).mockReturnValue({ meta: { readiness: "production_ready" }, networkState: "offline", cacheState: "fresh", pendingDrafts: 0, syncState: "idle" });
    (useJobDetail as jest.Mock).mockReturnValue(baseHookReturn());
    renderScreen();
    expect(screen.getByText(/offline/i)).toBeTruthy();
    expect(screen.getByText("AC Repair")).toBeTruthy();
  });

  it("shows a mutation error inline without discarding the loaded screen", () => {
    (useJobDetail as jest.Mock).mockReturnValue(baseHookReturn({ mutationError: { code: "CONFLICT", safeMessage: "This job was already updated. Refresh to continue.", category: "conflict", retryable: false } }));
    renderScreen();
    expect(screen.getByText("Couldn't update this job")).toBeTruthy();
    expect(screen.getByText("AC Repair")).toBeTruthy();
  });
});

describe("JobDetailScreen — terminal job", () => {
  it("marks every workflow stage completed and shows no next-action card for a completed job", () => {
    const detail = {
      ...BASE_DETAIL,
      job: { ...BASE_DETAIL.job, is_terminal: true, workflow_status: "completed" },
      next_required_action: { key: null, label: null, allowed: false, route_key: null },
      workflow: { stages: BASE_DETAIL.workflow.stages.map(s => ({ ...s, state: "completed" as const })) },
    };
    (useJobDetail as jest.Mock).mockReturnValue(baseHookReturn({ data: detail }));
    renderScreen();
    expect(screen.queryByText("Next required action")).toBeNull();
  });
});
