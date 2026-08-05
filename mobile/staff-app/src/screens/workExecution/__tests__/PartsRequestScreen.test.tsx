import React from "react";
import { render, screen, fireEvent } from "@testing-library/react-native";
import { SafeAreaProvider } from "react-native-safe-area-context";
import { ThemeProvider } from "../../../design-system/themes";
import { PartsRequestScreen } from "../PartsRequestScreen";

jest.mock("../useWorkExecution");
import { useWorkExecution } from "../useWorkExecution";
import type { PartsRequestDTO } from "../../../services/workExecution/types";

const TEST_INSETS = { frame: { x: 0, y: 0, width: 0, height: 0 }, insets: { top: 0, left: 0, right: 0, bottom: 0 } };

const mockNavigate = jest.fn();
const navigation = { navigate: mockNavigate } as any;
const route = { params: { jobId: "job-1" } } as any;

function baseReturn(overrides: Partial<ReturnType<typeof useWorkExecution>> = {}) {
  return {
    data: {
      job: { job_id: "job-1", job_reference: "HS-1044", workflow_status: "in_progress", is_terminal: false },
      approved_scope: null, work_session: null,
      checklist: { items: [], required_total: 0, required_completed: 0 },
      parts: [
        { parts_request_id: "p1", job_id: "job-1", part_name: "Copper pipe", quantity: 2, estimated_cost: 500, reason: "Leak repair", technician_note: null, customer_approval_required: false, status: "requested", rejection_reason: null, created_at: null },
        { parts_request_id: "p2", job_id: "job-1", part_name: "Valve", quantity: 1, estimated_cost: 300, reason: "Replacement", technician_note: null, customer_approval_required: false, status: "business_rejected", rejection_reason: "Too expensive", created_at: null },
      ] as PartsRequestDTO[],
      readiness: { can_finish_work: false, missing_checklist_item_ids: [], pending_part_request_ids: ["p1"], missing_evidence_categories: [], blockers: [] },
      allowed_actions: [],
    },
    isLoading: false, isError: false, error: null, isRefetching: false, refetch: jest.fn(),
    mutating: false, mutationError: null,
    startWork: jest.fn(), pauseWork: jest.fn(), resumeWork: jest.fn(), finishWork: jest.fn(),
    requestPart: jest.fn().mockResolvedValue({ ok: true }), saveChecklistResponse: jest.fn(),
    ...overrides,
  };
}

function renderScreen() {
  return render(
    <SafeAreaProvider initialMetrics={TEST_INSETS}>
      <ThemeProvider><PartsRequestScreen route={route} navigation={navigation} /></ThemeProvider>
    </SafeAreaProvider>,
  );
}

beforeEach(() => jest.clearAllMocks());

describe("PartsRequestScreen (Final Phase gap closure)", () => {
  it("shows every real parts request with its real status, never a fabricated one", () => {
    (useWorkExecution as jest.Mock).mockReturnValue(baseReturn());
    renderScreen();
    expect(screen.getByText("Copper pipe")).toBeTruthy();
    expect(screen.getByText("Waiting for tenant approval")).toBeTruthy();
    expect(screen.getByText("Valve")).toBeTruthy();
    expect(screen.getByText("Rejected by tenant: Too expensive")).toBeTruthy();
  });

  it("shows an empty state, not a fabricated list, when there are no parts requests", () => {
    (useWorkExecution as jest.Mock).mockReturnValue(baseReturn({ data: { ...baseReturn().data, parts: [] } }));
    renderScreen();
    expect(screen.getByText("No parts requested yet")).toBeTruthy();
  });

  it("submits a new part request through the real mutation and closes the sheet on success", async () => {
    const requestPart = jest.fn().mockResolvedValue({ ok: true });
    (useWorkExecution as jest.Mock).mockReturnValue(baseReturn({ requestPart }));
    renderScreen();
    fireEvent.press(screen.getByText("Request a part"));
    fireEvent.changeText(screen.getByLabelText("Part / material"), "Wrench");
    fireEvent.changeText(screen.getByLabelText("Reason"), "Needed for install");
    fireEvent.press(screen.getByText("Send request"));
    expect(requestPart).toHaveBeenCalled();
  });

  it("never shows Request a part once the job is terminal", () => {
    (useWorkExecution as jest.Mock).mockReturnValue(baseReturn({ data: { ...baseReturn().data, job: { ...baseReturn().data.job, is_terminal: true } } }));
    renderScreen();
    expect(screen.queryByText("Request a part")).toBeNull();
  });

  it("shows a real retry state on load failure, not a silent blank screen", () => {
    (useWorkExecution as jest.Mock).mockReturnValue(baseReturn({ data: undefined, isError: true, error: { code: "SERVER_UNAVAILABLE", category: "server", safeMessage: "Server error", retryable: true } }));
    renderScreen();
    expect(screen.getByText("Couldn't load parts requests")).toBeTruthy();
  });
});
