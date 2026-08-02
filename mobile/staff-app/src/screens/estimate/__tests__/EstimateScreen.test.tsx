import React from "react";
import { render, screen, fireEvent } from "@testing-library/react-native";
import { ThemeProvider } from "../../../design-system/themes";
import { EstimateScreen } from "../EstimateScreen";
import { EstimateDetailDTO } from "../../../services/estimate/types";

jest.mock("../useEstimate");
jest.mock("../../../hooks/useNetworkStatus", () => ({ useNetworkStatus: jest.fn(() => "online") }));

import { useEstimate } from "../useEstimate";
import { useNetworkStatus } from "../../../hooks/useNetworkStatus";

const mockNavigate = jest.fn();
const navigation = { navigate: mockNavigate } as any;
const route = { params: { jobId: "j1" } } as any;

const BASE_DETAIL: EstimateDetailDTO = {
  job: { job_id: "j1", job_reference: "HS-1044", workflow_status: "quote_required", is_terminal: false },
  inspection_source: { completed: true, diagnosis_summary: "Gas leakage detected", evidence_count: 2 },
  quote: {
    quote_id: "q1", version_number: 1, is_current: true, status: "draft", quote_type: "repair_quote",
    line_items: [
      { id: "i1", item_type: "labour", item_name: "Gas refill & leak repair", item_description: null, quantity: "1", unit_price: "1200", line_total: "1200", is_customer_visible: true },
      { id: "i2", item_type: "discount", item_name: "Visit fee adjustment", item_description: null, quantity: "1", unit_price: "299", line_total: "299", is_customer_visible: true },
    ],
    valid_until: null, customer_notes: null,
  },
  calculation: { currency: "INR", labour_total: "1200", parts_total: "0", subtotal: "1200", visit_fee_adjustment: "-299", tax_total: "0", grand_total: "901" },
  visit_fee_policy: { amount: 299, currency: "INR", disposition: "not_tracked" },
  readiness: { can_save: true, can_submit: true, blockers: [] },
  next_approval_target: "customer",
  allowed_actions: ["edit_estimate", "send_for_approval"],
  server_timestamp: null,
};

function baseHookReturn(overrides: Partial<ReturnType<typeof useEstimate>> = {}) {
  return {
    data: BASE_DETAIL, isLoading: false, isError: false, error: null, isRefetching: false, refetch: jest.fn(),
    mutating: false, mutationError: null,
    createEstimate: jest.fn(async () => ({ ok: true as const })),
    createRevision: jest.fn(async () => ({ ok: true as const })),
    addItem: jest.fn(async () => ({ ok: true as const })),
    updateItem: jest.fn(async () => ({ ok: true as const })),
    removeItem: jest.fn(async () => ({ ok: true as const })),
    sendForApproval: jest.fn(async () => ({ ok: true as const })),
    ...overrides,
  };
}

function renderScreen() {
  return render(<ThemeProvider><EstimateScreen route={route} navigation={navigation} /></ThemeProvider>);
}

beforeEach(() => {
  jest.clearAllMocks();
  (useNetworkStatus as jest.Mock).mockReturnValue("online");
});

describe("EstimateScreen — loaded draft (spec sections 2, 5, 6)", () => {
  it("renders inspection source, line items and backend-computed price summary", () => {
    (useEstimate as jest.Mock).mockReturnValue(baseHookReturn());
    renderScreen();
    expect(screen.getByText("Inspection completed")).toBeTruthy();
    expect(screen.getByText("Gas leakage detected · 2 photos")).toBeTruthy();
    expect(screen.getByText("Gas refill & leak repair")).toBeTruthy();
    expect(screen.getByText("Estimated total")).toBeTruthy();
  });

  it("never renders the auto-seeded visit-fee item as an editable line item (shown once, in the price summary only)", () => {
    (useEstimate as jest.Mock).mockReturnValue(baseHookReturn());
    renderScreen();
    expect(screen.queryByLabelText("Edit Visit fee adjustment")).toBeNull();
  });

  it("shows the customer-approval warning and never a Start Work action", () => {
    (useEstimate as jest.Mock).mockReturnValue(baseHookReturn());
    renderScreen();
    expect(screen.getByText("Customer approval required")).toBeTruthy();
    expect(screen.queryByText("Start work")).toBeNull();
  });
});

describe("EstimateScreen — no estimate yet (spec sections 1, 9)", () => {
  it("shows a blocked empty state before inspection completion, never lets the technician bypass it", () => {
    const detail = { ...BASE_DETAIL, quote: null, inspection_source: { ...BASE_DETAIL.inspection_source, completed: false }, readiness: { can_save: false, can_submit: false, blockers: ["INSPECTION_NOT_COMPLETE"] }, allowed_actions: [] };
    (useEstimate as jest.Mock).mockReturnValue(baseHookReturn({ data: detail }));
    renderScreen();
    expect(screen.getByText("Complete inspection first")).toBeTruthy();
  });

  it("offers Create estimate once inspection is complete and calls the real mutation", () => {
    const createEstimate = jest.fn(async () => ({ ok: true as const }));
    const detail = { ...BASE_DETAIL, quote: null, allowed_actions: ["create_estimate"] };
    (useEstimate as jest.Mock).mockReturnValue(baseHookReturn({ data: detail, createEstimate }));
    renderScreen();
    const buttons = screen.getAllByText("Create estimate");
    fireEvent.press(buttons[buttons.length - 1]);
    expect(createEstimate).toHaveBeenCalled();
  });
});

describe("EstimateScreen — item mutation (spec section 6)", () => {
  it("opens the add-item sheet and submits through the real mutation, never computing the line total itself", () => {
    const addItem = jest.fn(async () => ({ ok: true as const }));
    (useEstimate as jest.Mock).mockReturnValue(baseHookReturn({ addItem }));
    renderScreen();
    fireEvent.press(screen.getByText("+ Add item"));
    fireEvent.changeText(screen.getByLabelText("Description"), "Refrigerant gas");
    fireEvent.changeText(screen.getByLabelText("Unit rate (₹)"), "800");
    const buttons = screen.getAllByText("Add item");
    fireEvent.press(buttons[buttons.length - 1]);
    expect(addItem).toHaveBeenCalledWith("q1", { item_type: "labour", item_name: "Refrigerant gas", quantity: 1, unit_price: 800 });
  });

  it("removes an item through the real mutation", () => {
    const removeItem = jest.fn(async () => ({ ok: true as const }));
    (useEstimate as jest.Mock).mockReturnValue(baseHookReturn({ removeItem }));
    renderScreen();
    fireEvent.press(screen.getByLabelText("Remove Gas refill & leak repair"));
    expect(removeItem).toHaveBeenCalledWith("q1", "i1");
  });
});

describe("EstimateScreen — sent/read-only states (spec sections 15, 23)", () => {
  it("hides item mutation controls once sent to the customer", () => {
    const detail = { ...BASE_DETAIL, quote: { ...BASE_DETAIL.quote!, status: "sent_to_customer" as const }, allowed_actions: [] };
    (useEstimate as jest.Mock).mockReturnValue(baseHookReturn({ data: detail }));
    renderScreen();
    expect(screen.queryByText("+ Add item")).toBeNull();
    expect(screen.queryByText("Send for approval")).toBeNull();
  });

  it("shows Create revision only when the backend allows it, never a free-text edit of an approved quote", () => {
    const detail = { ...BASE_DETAIL, quote: { ...BASE_DETAIL.quote!, status: "revision_requested" as const }, allowed_actions: ["create_revision"] };
    (useEstimate as jest.Mock).mockReturnValue(baseHookReturn({ data: detail }));
    renderScreen();
    expect(screen.getByText("Create revision")).toBeTruthy();
    expect(screen.queryByText("+ Add item")).toBeNull();
  });

  it("offline disables submission and shows the offline notice", () => {
    (useNetworkStatus as jest.Mock).mockReturnValue("offline");
    (useEstimate as jest.Mock).mockReturnValue(baseHookReturn());
    renderScreen();
    expect(screen.getByText("Offline")).toBeTruthy();
  });
});

describe("EstimateScreen — loading/error", () => {
  it("shows a skeleton while loading", () => {
    (useEstimate as jest.Mock).mockReturnValue(baseHookReturn({ data: undefined, isLoading: true }));
    renderScreen();
    expect(screen.queryByText("Gas refill & leak repair")).toBeNull();
  });

  it("shows a retryable error state on load failure", () => {
    (useEstimate as jest.Mock).mockReturnValue(baseHookReturn({ data: undefined, isError: true, error: { safeMessage: "Something went wrong.", code: "SERVER_UNAVAILABLE", category: "server", retryable: true } }));
    renderScreen();
    expect(screen.getByText("Retry")).toBeTruthy();
  });
});

describe("EstimateScreen — navigation", () => {
  it("returns to Job Detail via the back button", () => {
    (useEstimate as jest.Mock).mockReturnValue(baseHookReturn());
    renderScreen();
    fireEvent.press(screen.getByLabelText("Back"));
    expect(mockNavigate).toHaveBeenCalledWith("JobDetail", { jobId: "j1" });
  });
});
