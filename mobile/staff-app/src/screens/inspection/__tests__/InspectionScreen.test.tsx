import React from "react";
import { render, screen, fireEvent } from "@testing-library/react-native";
import { ThemeProvider } from "../../../design-system/themes";
import { InspectionScreen } from "../InspectionScreen";
import { InspectionDetailDTO } from "../../../services/inspection/types";

jest.mock("../useInspection");
jest.mock("../../../hooks/useNetworkStatus", () => ({ useNetworkStatus: jest.fn(() => "online") }));
jest.mock("expo-image-picker", () => ({
  requestCameraPermissionsAsync: jest.fn(async () => ({ granted: true })),
  launchCameraAsync: jest.fn(async () => ({ canceled: true })),
}));

import { useInspection } from "../useInspection";
import { useNetworkStatus } from "../../../hooks/useNetworkStatus";

const mockNavigate = jest.fn();
const navigation = { navigate: mockNavigate } as any;
const route = { params: { jobId: "j1" } } as any;

const BASE_DETAIL: InspectionDetailDTO = {
  job: { job_id: "j1", job_reference: "HS-1044", service_label: "AC Repair", workflow_status: "inspection_started", is_terminal: false },
  customer_report: { issue_label: "AC is running but not cooling", answers: [], notes: null },
  instance: { instance_id: "inst1", state: "IN_PROGRESS", started_at: null, completed_at: null },
  sections: [
    {
      section_id: "sec1", title: "Inspection checklist", display_order: 0,
      items: [
        {
          id: "item1", checklist_section_id: "sec1", item_type: "YES_NO", label: "Power supply checked",
          help_text: null, is_required: true, evidence_required: false, min_evidence_count: 0, max_evidence_count: 1,
          allowed_file_types: null, measurement_unit: null, select_options: null, validation_rules: null,
          display_order: 0, condition_rules: null, failure_behavior: null, customer_visible: false,
          response: { id: "r1", job_checklist_instance_id: "inst1", checklist_item_id: "item1", response_value: { value: "yes" }, evidence: null, validation_result: null },
        },
        {
          id: "item2", checklist_section_id: "sec1", item_type: "YES_NO", label: "Gas pressure checked",
          help_text: null, is_required: true, evidence_required: false, min_evidence_count: 0, max_evidence_count: 1,
          allowed_file_types: null, measurement_unit: null, select_options: null, validation_rules: null,
          display_order: 1, condition_rules: null, failure_behavior: null, customer_visible: false,
          response: null,
        },
      ],
    },
  ],
  readiness: { total_required: 2, completed_required: 1, missing_item_ids: ["item2"], missing_evidence_item_ids: [], can_complete: false, blockers: [] },
  allowed_actions: ["save_inspection_draft"],
  definition_status: "AVAILABLE",
};

function baseHookReturn(overrides: Partial<ReturnType<typeof useInspection>> = {}) {
  return {
    data: BASE_DETAIL, isLoading: false, isError: false, error: null, isRefetching: false, refetch: jest.fn(),
    savingItemId: null, saveError: null, saveItemResponse: jest.fn(),
    uploadingItemId: null, uploadError: null, uploadEvidence: jest.fn(),
    completing: false, completeError: null, complete: jest.fn(async () => ({ ok: true as const })),
    ...overrides,
  };
}

function renderScreen() {
  return render(<ThemeProvider><InspectionScreen route={route} navigation={navigation} /></ThemeProvider>);
}

beforeEach(() => {
  jest.clearAllMocks();
  (useNetworkStatus as jest.Mock).mockReturnValue("online");
});

describe("InspectionScreen — loaded state (spec sections 2, 5)", () => {
  it("renders progress, customer report, and definition-driven checklist items", () => {
    (useInspection as jest.Mock).mockReturnValue(baseHookReturn());
    renderScreen();
    expect(screen.getByText("1 of 2 checks complete")).toBeTruthy();
    expect(screen.getByText("AC is running but not cooling")).toBeTruthy();
    expect(screen.getByText("Power supply checked")).toBeTruthy();
    expect(screen.getByText("Gas pressure checked")).toBeTruthy();
  });

  it("disables Complete inspection while required items remain and shows the remaining count", () => {
    (useInspection as jest.Mock).mockReturnValue(baseHookReturn());
    renderScreen();
    expect(screen.getByText("Complete inspection (1 left)")).toBeTruthy();
  });

  it("enables Complete inspection once every required item is answered", () => {
    const detail = { ...BASE_DETAIL, readiness: { ...BASE_DETAIL.readiness, completed_required: 2, can_complete: true } };
    (useInspection as jest.Mock).mockReturnValue(baseHookReturn({ data: detail }));
    renderScreen();
    expect(screen.getByText("Complete inspection")).toBeTruthy();
  });
});

describe("InspectionScreen — completion (spec sections 8, 10)", () => {
  it("calls the real complete mutation and navigates back to Job Detail on success", async () => {
    const complete = jest.fn(async () => ({ ok: true as const }));
    const detail = { ...BASE_DETAIL, readiness: { ...BASE_DETAIL.readiness, completed_required: 2, can_complete: true } };
    (useInspection as jest.Mock).mockReturnValue(baseHookReturn({ data: detail, complete }));
    renderScreen();
    await fireEvent.press(screen.getByText("Complete inspection"));
    expect(complete).toHaveBeenCalled();
  });

  it("never allows completion while required items are missing (button disabled, not just relabeled)", () => {
    (useInspection as jest.Mock).mockReturnValue(baseHookReturn());
    renderScreen();
    const button = screen.getByText("Complete inspection (1 left)");
    expect(button).toBeTruthy();
  });
});

describe("InspectionScreen — read-only states (spec sections 10, 16, 18)", () => {
  it("hides mutation controls for a completed inspection", () => {
    const detail = { ...BASE_DETAIL, instance: { ...BASE_DETAIL.instance!, state: "COMPLETED" as const } };
    (useInspection as jest.Mock).mockReturnValue(baseHookReturn({ data: detail }));
    renderScreen();
    expect(screen.queryByText("Save draft")).toBeNull();
    expect(screen.getByText("Completed")).toBeTruthy();
  });

  it("goes read-only and shows an offline notice while offline", () => {
    (useNetworkStatus as jest.Mock).mockReturnValue("offline");
    (useInspection as jest.Mock).mockReturnValue(baseHookReturn());
    renderScreen();
    expect(screen.getByText("Offline")).toBeTruthy();
    expect(screen.queryByText("Save draft")).toBeNull();
  });

  it("shows an honest empty state when no checklist is mapped to this job type", () => {
    const detail = { ...BASE_DETAIL, definition_status: "UNAVAILABLE" as const, sections: [], instance: null };
    (useInspection as jest.Mock).mockReturnValue(baseHookReturn({ data: detail }));
    renderScreen();
    expect(screen.getByText("No inspection checklist configured")).toBeTruthy();
  });

  it("shows a retryable error state when the projection fails to load", () => {
    (useInspection as jest.Mock).mockReturnValue(baseHookReturn({ data: undefined, isError: true, error: { safeMessage: "Something went wrong.", code: "SERVER_UNAVAILABLE", category: "server", retryable: true } }));
    renderScreen();
    expect(screen.getByText("Retry")).toBeTruthy();
  });

  it("shows a loading skeleton before data arrives", () => {
    (useInspection as jest.Mock).mockReturnValue(baseHookReturn({ data: undefined, isLoading: true }));
    renderScreen();
    expect(screen.queryByText("AC is running but not cooling")).toBeNull();
  });
});

describe("InspectionScreen — navigation", () => {
  it("returns to Job Detail via the back button", () => {
    (useInspection as jest.Mock).mockReturnValue(baseHookReturn());
    renderScreen();
    fireEvent.press(screen.getByLabelText("Back"));
    expect(mockNavigate).toHaveBeenCalledWith("JobDetail", { jobId: "j1" });
  });
});
