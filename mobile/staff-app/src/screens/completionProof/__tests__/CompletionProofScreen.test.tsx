import React from "react";
import { render, screen, fireEvent } from "@testing-library/react-native";
import { ThemeProvider } from "../../../design-system/themes";
import { CompletionProofScreen } from "../CompletionProofScreen";
import { CompletionProofDetailDTO } from "../../../services/completionProof/types";

jest.mock("../useCompletionProof");
jest.mock("../../../hooks/useNetworkStatus", () => ({ useNetworkStatus: jest.fn(() => "online") }));
jest.mock("expo-image-picker", () => ({
  requestCameraPermissionsAsync: jest.fn(async () => ({ granted: true })),
  launchCameraAsync: jest.fn(async () => ({ canceled: true })),
}));

import { useCompletionProof } from "../useCompletionProof";
import { useNetworkStatus } from "../../../hooks/useNetworkStatus";

const mockNavigate = jest.fn();
const navigation = { navigate: mockNavigate } as any;
const route = { params: { jobId: "j1" } } as any;

const BASE_DETAIL: CompletionProofDetailDTO = {
  job: { job_id: "j1", job_reference: "HS-1044", workflow_status: "work_done", is_terminal: false },
  work_summary: { work_finished_at: "2026-07-31T08:18:00Z", work_session_id: "s1", approved_quote_id: "q1", approved_quote_version: 1 },
  proof: {
    proof_id: "p1", job_id: "j1", status: "draft", resolution_summary: "Gas leakage repaired and refrigerant refilled.",
    final_service_notes: null, before_photo_ids: ["b1"], after_photo_ids: ["a1"], handover_status: "not_requested",
    handover_requested_at: null, handover_last_reminder_at: null, submitted_by: null, submitted_at: null,
  },
  definition: {
    customer_handover_required: true,
    final_checks: [
      { id: "c1", checklist_section_id: "s1", item_type: "YES_NO", label: "Cooling tested", help_text: null, is_required: true, evidence_required: false, min_evidence_count: 0, max_evidence_count: 1, allowed_file_types: null, measurement_unit: null, select_options: null, validation_rules: null, display_order: 0, condition_rules: null, failure_behavior: null, customer_visible: false, response: { id: "r1", job_checklist_instance_id: "i1", checklist_item_id: "c1", response_value: { value: "yes" }, evidence: null, validation_result: null } },
      { id: "c2", checklist_section_id: "s1", item_type: "YES_NO", label: "Customer shown completed work", help_text: null, is_required: true, evidence_required: false, min_evidence_count: 0, max_evidence_count: 1, allowed_file_types: null, measurement_unit: null, select_options: null, validation_rules: null, display_order: 1, condition_rules: null, failure_behavior: null, customer_visible: false, response: null },
    ] as any,
  },
  parts_used: [
    { parts_request_id: "p1", part_name: "Refrigerant gas", quantity: 1, estimated_cost: 800, status: "installed" },
    { parts_request_id: "p2", part_name: "Copper pipe", quantity: 2, estimated_cost: 400, status: "business_approved" },
  ],
  readiness: { can_submit: false, missing_check_ids: ["c2"], missing_evidence_categories: [], unresolved_parts: [], blockers: ["FINAL_CHECKS_INCOMPLETE"] },
  final_checks_progress: { required_total: 2, required_completed: 1 },
  allowed_actions: ["save_draft"],
};

function baseHookReturn(overrides: Partial<ReturnType<typeof useCompletionProof>> = {}) {
  return {
    data: BASE_DETAIL, isLoading: false, isError: false, error: null, isRefetching: false, refetch: jest.fn(),
    mutating: false, mutationError: null, uploadingCategory: null,
    saveDraft: jest.fn(async () => ({ ok: true as const })),
    addEvidenceFromUpload: jest.fn(async () => ({ ok: true as const })),
    removeEvidence: jest.fn(async () => ({ ok: true as const })),
    submit: jest.fn(async () => ({ ok: true as const })),
    requestHandover: jest.fn(async () => ({ ok: true as const })),
    sendReminder: jest.fn(async () => ({ ok: true as const })),
    markCustomerUnavailable: jest.fn(async () => ({ ok: true as const })),
    ...overrides,
  };
}

function renderScreen() {
  return render(<ThemeProvider><CompletionProofScreen route={route} navigation={navigation} /></ThemeProvider>);
}

beforeEach(() => {
  jest.clearAllMocks();
  (useNetworkStatus as jest.Mock).mockReturnValue("online");
});

describe("CompletionProofScreen — draft state (spec sections 2, 5, 7, 8, 9)", () => {
  it("renders the work-finished banner, resolution summary, final checks, evidence and parts used", () => {
    (useCompletionProof as jest.Mock).mockReturnValue(baseHookReturn());
    renderScreen();
    expect(screen.getByText("Work finished")).toBeTruthy();
    expect(screen.getByText("Cooling tested")).toBeTruthy();
    expect(screen.getByText("Customer shown completed work")).toBeTruthy();
    expect(screen.getByText("Refrigerant gas · Qty 1")).toBeTruthy();
  });

  it("labels before/after evidence explicitly, not by color alone", () => {
    (useCompletionProof as jest.Mock).mockReturnValue(baseHookReturn());
    renderScreen();
    expect(screen.getByText("Before")).toBeTruthy();
    expect(screen.getByText("After")).toBeTruthy();
  });

  it("shows the payment/completion disclaimer banner", () => {
    (useCompletionProof as jest.Mock).mockReturnValue(baseHookReturn());
    renderScreen();
    expect(screen.getByText("Submitting proof does not confirm payment or complete the job.")).toBeTruthy();
  });

  it("disables Submit while a required final check is missing", () => {
    const submit = jest.fn(async () => ({ ok: true as const }));
    (useCompletionProof as jest.Mock).mockReturnValue(baseHookReturn({ submit }));
    renderScreen();
    fireEvent.press(screen.getByText("Submit completion proof"));
    expect(submit).not.toHaveBeenCalled();
  });

  it("enables and calls Submit once readiness allows it", () => {
    const submit = jest.fn(async () => ({ ok: true as const }));
    const detail = { ...BASE_DETAIL, readiness: { ...BASE_DETAIL.readiness, can_submit: true, blockers: [] }, allowed_actions: ["save_draft", "submit_proof"] };
    (useCompletionProof as jest.Mock).mockReturnValue(baseHookReturn({ data: detail, submit }));
    renderScreen();
    fireEvent.press(screen.getByText("Submit completion proof"));
    expect(submit).toHaveBeenCalled();
  });

  it("saves the draft resolution summary through the real mutation on blur", () => {
    const saveDraft = jest.fn(async () => ({ ok: true as const }));
    (useCompletionProof as jest.Mock).mockReturnValue(baseHookReturn({ saveDraft }));
    renderScreen();
    const field = screen.getByPlaceholderText("Describe the diagnosed issue, work performed and final test result…");
    fireEvent.changeText(field, "Updated summary");
    fireEvent(field, "blur");
    expect(saveDraft).toHaveBeenCalled();
  });
});

describe("CompletionProofScreen — never shows payment controls (spec scope exclusions)", () => {
  it("never renders a payment amount/method control", () => {
    (useCompletionProof as jest.Mock).mockReturnValue(baseHookReturn());
    renderScreen();
    expect(screen.queryByText("Mark as paid")).toBeNull();
    expect(screen.queryByText("Amount received")).toBeNull();
  });
});

describe("CompletionProofScreen — submitted / handover (spec section 10)", () => {
  it("hides Save/Submit and shows the customer-handover card once submitted", () => {
    const detail = { ...BASE_DETAIL, proof: { ...BASE_DETAIL.proof, status: "submitted" as const }, allowed_actions: ["request_handover"] };
    (useCompletionProof as jest.Mock).mockReturnValue(baseHookReturn({ data: detail }));
    renderScreen();
    expect(screen.queryByText("Submit completion proof")).toBeNull();
    expect(screen.getByText("Customer handover")).toBeTruthy();
    expect(screen.getByText("Not requested")).toBeTruthy();
  });

  it("requests handover through the real mutation, never a technician-side accept", () => {
    const requestHandover = jest.fn(async () => ({ ok: true as const }));
    const detail = { ...BASE_DETAIL, proof: { ...BASE_DETAIL.proof, status: "submitted" as const }, allowed_actions: ["request_handover"] };
    (useCompletionProof as jest.Mock).mockReturnValue(baseHookReturn({ data: detail, requestHandover }));
    renderScreen();
    fireEvent.press(screen.getByText("Request"));
    expect(requestHandover).toHaveBeenCalled();
    expect(screen.queryByText("Customer accepted")).toBeNull();
  });

  it("shows acknowledgment-pending state and a reminder action", () => {
    const detail = { ...BASE_DETAIL, proof: { ...BASE_DETAIL.proof, status: "submitted" as const, handover_status: "requested" as const }, allowed_actions: ["send_reminder", "mark_customer_unavailable"] };
    (useCompletionProof as jest.Mock).mockReturnValue(baseHookReturn({ data: detail }));
    renderScreen();
    expect(screen.getByText("Acknowledgment pending")).toBeTruthy();
    expect(screen.getByText("Send reminder")).toBeTruthy();
  });
});

describe("CompletionProofScreen — read-only/offline/blocked states", () => {
  it("blocks entry with an honest message when work isn't finished yet", () => {
    const detail = { ...BASE_DETAIL, job: { ...BASE_DETAIL.job, workflow_status: "service_started" } };
    (useCompletionProof as jest.Mock).mockReturnValue(baseHookReturn({ data: detail }));
    renderScreen();
    expect(screen.getByText("Work isn't finished yet")).toBeTruthy();
  });

  it("goes read-only offline", () => {
    (useNetworkStatus as jest.Mock).mockReturnValue("offline");
    (useCompletionProof as jest.Mock).mockReturnValue(baseHookReturn());
    renderScreen();
    expect(screen.getByText("Offline")).toBeTruthy();
    expect(screen.queryByText("Submit completion proof")).toBeNull();
  });

  it("shows a loading skeleton", () => {
    (useCompletionProof as jest.Mock).mockReturnValue(baseHookReturn({ data: undefined, isLoading: true }));
    renderScreen();
    expect(screen.queryByText("Work finished")).toBeNull();
  });

  it("shows a retryable error state", () => {
    (useCompletionProof as jest.Mock).mockReturnValue(baseHookReturn({ data: undefined, isError: true, error: { safeMessage: "Something went wrong.", code: "SERVER_UNAVAILABLE", category: "server", retryable: true } }));
    renderScreen();
    expect(screen.getByText("Retry")).toBeTruthy();
  });

  it("returns to Job Detail via the back button", () => {
    (useCompletionProof as jest.Mock).mockReturnValue(baseHookReturn());
    renderScreen();
    fireEvent.press(screen.getByLabelText("Back"));
    expect(mockNavigate).toHaveBeenCalledWith("JobDetail", { jobId: "j1" });
  });
});
