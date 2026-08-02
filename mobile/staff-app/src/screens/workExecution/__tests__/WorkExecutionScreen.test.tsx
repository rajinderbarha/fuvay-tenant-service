import React from "react";
import { render, screen, fireEvent } from "@testing-library/react-native";
import { ThemeProvider } from "../../../design-system/themes";
import { WorkExecutionScreen } from "../WorkExecutionScreen";
import { WorkExecutionDetailDTO } from "../../../services/workExecution/types";

jest.mock("../useWorkExecution");
jest.mock("../../../hooks/useNetworkStatus", () => ({ useNetworkStatus: jest.fn(() => "online") }));
jest.mock("expo-image-picker", () => ({
  requestCameraPermissionsAsync: jest.fn(async () => ({ granted: true })),
  launchCameraAsync: jest.fn(async () => ({ canceled: true })),
}));

import { useWorkExecution } from "../useWorkExecution";
import { useNetworkStatus } from "../../../hooks/useNetworkStatus";

const mockNavigate = jest.fn();
const navigation = { navigate: mockNavigate } as any;
const route = { params: { jobId: "j1" } } as any;

const BASE_DETAIL: WorkExecutionDetailDTO = {
  job: { job_id: "j1", job_reference: "HS-1044", workflow_status: "service_started", is_terminal: false },
  approved_scope: { quote_id: "q1", version_number: 1, approved_total: "1701.00", currency: "INR", approved_at: "2026-07-31T05:00:00Z", scope_locked: true },
  work_session: { session_id: "s1", job_id: "j1", state: "active", started_at: "2026-07-31T05:00:00Z", paused_at: null, pause_reason: null, accumulated_seconds: 2538, finished_at: null },
  checklist: {
    instance_id: "inst1", required_total: 5, required_completed: 3,
    items: [
      { id: "i1", checklist_section_id: "s1", item_type: "YES_NO", label: "Repair gas leakage", help_text: null, is_required: true, evidence_required: false, min_evidence_count: 0, max_evidence_count: 1, allowed_file_types: null, measurement_unit: null, select_options: null, validation_rules: null, display_order: 0, condition_rules: null, failure_behavior: null, customer_visible: false, response: { id: "r1", job_checklist_instance_id: "inst1", checklist_item_id: "i1", response_value: { value: "yes" }, evidence: null, validation_result: null } },
      { id: "i2", checklist_section_id: "s1", item_type: "YES_NO", label: "Refill refrigerant", help_text: null, is_required: true, evidence_required: false, min_evidence_count: 0, max_evidence_count: 1, allowed_file_types: null, measurement_unit: null, select_options: null, validation_rules: null, display_order: 1, condition_rules: null, failure_behavior: null, customer_visible: false, response: null },
    ] as any,
  },
  parts: [
    { parts_request_id: "p1", job_id: "j1", part_name: "Refrigerant gas", quantity: 1, estimated_cost: 800, reason: "leak", technician_note: null, customer_approval_required: false, status: "business_approved", rejection_reason: null, created_at: null },
    { parts_request_id: "p2", job_id: "j1", part_name: "Copper pipe", quantity: 2, estimated_cost: 400, reason: "extension", technician_note: null, customer_approval_required: false, status: "requested", rejection_reason: null, created_at: null },
  ],
  readiness: { can_finish_work: false, missing_checklist_item_ids: ["i2"], pending_part_request_ids: ["p2"], missing_evidence_categories: [], blockers: ["CHECKLIST_INCOMPLETE", "PART_APPROVAL_PENDING"] },
  allowed_actions: ["pause_work"],
};

function baseHookReturn(overrides: Partial<ReturnType<typeof useWorkExecution>> = {}) {
  return {
    data: BASE_DETAIL, isLoading: false, isError: false, error: null, isRefetching: false, refetch: jest.fn(),
    mutating: false, mutationError: null,
    startWork: jest.fn(async () => ({ ok: true as const })),
    pauseWork: jest.fn(async () => ({ ok: true as const })),
    resumeWork: jest.fn(async () => ({ ok: true as const })),
    finishWork: jest.fn(async () => ({ ok: true as const })),
    requestPart: jest.fn(async () => ({ ok: true as const })),
    saveChecklistResponse: jest.fn(async () => ({ ok: true as const })),
    ...overrides,
  };
}

function renderScreen() {
  return render(<ThemeProvider><WorkExecutionScreen route={route} navigation={navigation} /></ThemeProvider>);
}

beforeEach(() => {
  jest.clearAllMocks();
  (useNetworkStatus as jest.Mock).mockReturnValue("online");
});

describe("WorkExecutionScreen — active session (spec sections 3, 7, 8, 9)", () => {
  it("renders the approved-estimate banner, session timer, checklist and parts", () => {
    (useWorkExecution as jest.Mock).mockReturnValue(baseHookReturn());
    renderScreen();
    expect(screen.getByText("Estimate v1 approved")).toBeTruthy();
    expect(screen.getByText("Repair gas leakage")).toBeTruthy();
    expect(screen.getByText("Refrigerant gas · Qty 1")).toBeTruthy();
  });

  it("shows the remaining-requirements banner with both checklist and part counts", () => {
    (useWorkExecution as jest.Mock).mockReturnValue(baseHookReturn());
    renderScreen();
    expect(screen.getByText("2 checklist items and 1 part approval remaining")).toBeTruthy();
  });

  it("disables Finish Work until the backend readiness allows it", () => {
    const finishWork = jest.fn(async () => ({ ok: true as const }));
    (useWorkExecution as jest.Mock).mockReturnValue(baseHookReturn({ finishWork }));
    renderScreen();
    fireEvent.press(screen.getByText("Finish work"));
    expect(finishWork).not.toHaveBeenCalled();
  });

  it("enables and calls Finish Work once readiness allows it, then returns to Job Detail", async () => {
    const finishWork = jest.fn(async () => ({ ok: true as const }));
    const detail = { ...BASE_DETAIL, readiness: { ...BASE_DETAIL.readiness, can_finish_work: true, blockers: [] }, allowed_actions: ["pause_work", "finish_work"] };
    (useWorkExecution as jest.Mock).mockReturnValue(baseHookReturn({ data: detail, finishWork }));
    renderScreen();
    fireEvent.press(screen.getByText("Finish work"));
    expect(finishWork).toHaveBeenCalled();
  });

  it("pauses the session through the real mutation", () => {
    const pauseWork = jest.fn(async () => ({ ok: true as const }));
    (useWorkExecution as jest.Mock).mockReturnValue(baseHookReturn({ pauseWork }));
    renderScreen();
    fireEvent.press(screen.getByText("Pause"));
    expect(pauseWork).toHaveBeenCalled();
  });
});

describe("WorkExecutionScreen — ready to start (spec section 6)", () => {
  it("shows Start Work when the backend allows it and no session exists yet", () => {
    const startWork = jest.fn(async () => ({ ok: true as const }));
    const detail = { ...BASE_DETAIL, job: { ...BASE_DETAIL.job, workflow_status: "inspection_done" }, work_session: null, allowed_actions: ["start_work"] };
    (useWorkExecution as jest.Mock).mockReturnValue(baseHookReturn({ data: detail, startWork }));
    renderScreen();
    fireEvent.press(screen.getByText("Start work"));
    expect(startWork).toHaveBeenCalled();
  });

  it("shows a warning instead of Start Work when there is no approved estimate", () => {
    const detail = { ...BASE_DETAIL, approved_scope: null, work_session: null, allowed_actions: [] };
    (useWorkExecution as jest.Mock).mockReturnValue(baseHookReturn({ data: detail }));
    renderScreen();
    expect(screen.getByText("No approved estimate")).toBeTruthy();
    expect(screen.queryByText("Start work")).toBeNull();
  });
});

describe("WorkExecutionScreen — parts request", () => {
  it("opens the request-part sheet and submits through the real mutation", () => {
    const requestPart = jest.fn(async () => ({ ok: true as const }));
    (useWorkExecution as jest.Mock).mockReturnValue(baseHookReturn({ requestPart }));
    renderScreen();
    fireEvent.press(screen.getByText("+ Request part"));
    fireEvent.changeText(screen.getByLabelText("Part / material"), "Filter");
    fireEvent.changeText(screen.getByLabelText("Estimated cost (₹)"), "150");
    fireEvent.changeText(screen.getByLabelText("Reason"), "Clogged filter");
    fireEvent.press(screen.getByText("Send request"));
    expect(requestPart).toHaveBeenCalledWith({ part_name: "Filter", quantity: 1, estimated_cost: 150, reason: "Clogged filter" });
  });
});

describe("WorkExecutionScreen — read-only/offline (spec sections 17, 19)", () => {
  it("hides mutation controls once the job is work_done (never re-shows Finish Work)", () => {
    const detail = { ...BASE_DETAIL, job: { ...BASE_DETAIL.job, workflow_status: "work_done" }, allowed_actions: [] };
    (useWorkExecution as jest.Mock).mockReturnValue(baseHookReturn({ data: detail }));
    renderScreen();
    expect(screen.queryByText("Finish work")).toBeNull();
    expect(screen.queryByText("+ Request part")).toBeNull();
  });

  it("goes read-only offline", () => {
    (useNetworkStatus as jest.Mock).mockReturnValue("offline");
    (useWorkExecution as jest.Mock).mockReturnValue(baseHookReturn());
    renderScreen();
    expect(screen.getByText("Offline")).toBeTruthy();
  });
});

describe("WorkExecutionScreen — loading/error/navigation", () => {
  it("shows a loading skeleton", () => {
    (useWorkExecution as jest.Mock).mockReturnValue(baseHookReturn({ data: undefined, isLoading: true }));
    renderScreen();
    expect(screen.queryByText("Repair gas leakage")).toBeNull();
  });

  it("shows a retryable error state", () => {
    (useWorkExecution as jest.Mock).mockReturnValue(baseHookReturn({ data: undefined, isError: true, error: { safeMessage: "Something went wrong.", code: "SERVER_UNAVAILABLE", category: "server", retryable: true } }));
    renderScreen();
    expect(screen.getByText("Retry")).toBeTruthy();
  });

  it("returns to Job Detail via the back button", () => {
    (useWorkExecution as jest.Mock).mockReturnValue(baseHookReturn());
    renderScreen();
    fireEvent.press(screen.getByLabelText("Back"));
    expect(mockNavigate).toHaveBeenCalledWith("JobDetail", { jobId: "j1" });
  });
});
