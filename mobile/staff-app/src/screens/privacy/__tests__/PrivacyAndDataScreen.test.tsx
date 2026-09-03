import React from "react";
import { render, screen, fireEvent } from "@testing-library/react-native";
import { ThemeProvider } from "../../../design-system/themes";
import { PrivacyAndDataScreen } from "../PrivacyAndDataScreen";
import { PrivacySummaryDTO, ConsentPurposeDTO } from "../../../services/privacy/types";

jest.mock("../usePrivacy");
jest.mock("../../../hooks/useNetworkStatus", () => ({ useNetworkStatus: jest.fn(() => ({ meta: { readiness: "production_ready" }, networkState: "online", cacheState: "fresh", pendingDrafts: 0, syncState: "idle" })) }));

import { usePrivacy } from "../usePrivacy";
import { useNetworkStatus } from "../../../hooks/useNetworkStatus";

const mockNavigate = jest.fn();
const navigation = { navigate: mockNavigate, goBack: jest.fn() } as any;
const route = { params: undefined } as any;

const SUMMARY: PrivacySummaryDTO = {
  privacy_status: { code: "request_in_progress", label: "Request in progress" },
  policy: { version: "1.0", effective_from: null },
  request_counts: { open: 1, completed: 2 },
  recent_request: {
    id: "r1", request_number: "PRV-2026-0042", request_type: "data_correction", status: "identity_verification_pending",
    status_label: "Identity Verification Required", sla_status: "on_track", verification_status: null,
    submitted_at: "2026-07-29T00:00:00Z", due_at: null, completed_at: null, reason: null, rejection_reason: null,
    created_at: "2026-07-29T00:00:00Z", updated_at: "2026-07-31T00:00:00Z",
  },
};

const CONSENTS: ConsentPurposeDTO[] = [
  { purpose_code: "service_communications", label: "Service communications", description: "Required for assigned jobs and account updates", legal_or_policy_basis: "contract_or_security", required: true, enabled: true, configurable: false, policy_version: "1.0", last_changed_at: null },
  { purpose_code: "product_improvement", label: "Product improvement", description: "Share anonymous app diagnostics", legal_or_policy_basis: "consent", required: false, enabled: true, configurable: true, policy_version: "1.0", last_changed_at: null },
  { purpose_code: "optional_updates", label: "Optional updates", description: "Tips and non-essential announcements", legal_or_policy_basis: "consent", required: false, enabled: false, configurable: true, policy_version: "1.0", last_changed_at: null },
];

function baseHookReturn(overrides: Partial<ReturnType<typeof usePrivacy>> = {}) {
  return {
    summary: SUMMARY, summaryLoading: false, summaryError: null, summaryIsError: false, refetchSummary: jest.fn(),
    consents: CONSENTS, consentsLoading: false,
    mutatingPurpose: null, mutationError: null, toggleConsent: jest.fn(),
    submitRequest: jest.fn(),
    ...overrides,
  };
}

function renderScreen() {
  return render(<ThemeProvider><PrivacyAndDataScreen route={route} navigation={navigation} /></ThemeProvider>);
}

beforeEach(() => {
  jest.clearAllMocks();
  (useNetworkStatus as jest.Mock).mockReturnValue({ meta: { readiness: "production_ready" }, networkState: "online", cacheState: "fresh", pendingDrafts: 0, syncState: "idle" });
});

describe("PrivacyAndDataScreen (Phase X)", () => {
  it("renders the backend-derived privacy status, never a fabricated default", () => {
    (usePrivacy as jest.Mock).mockReturnValue(baseHookReturn());
    renderScreen();
    expect(screen.getByText("Request in progress")).toBeTruthy();
  });

  it("locks required service communications with no toggle", () => {
    (usePrivacy as jest.Mock).mockReturnValue(baseHookReturn());
    renderScreen();
    expect(screen.getByText("Required")).toBeTruthy();
  });

  it("toggles an optional consent", () => {
    const toggleConsent = jest.fn();
    (usePrivacy as jest.Mock).mockReturnValue(baseHookReturn({ toggleConsent }));
    renderScreen();
    fireEvent(screen.getByLabelText("Product improvement, on"), "valueChange", false);
    expect(toggleConsent).toHaveBeenCalledWith("product_improvement", false);
  });

  it("shows the recent request card with Track request navigation", () => {
    (usePrivacy as jest.Mock).mockReturnValue(baseHookReturn());
    renderScreen();
    expect(screen.getByText("PRV-2026-0042")).toBeTruthy();
    fireEvent.press(screen.getByText("Track request"));
    expect(mockNavigate).toHaveBeenCalledWith("PrivacyRequestDetail", { requestId: "r1" });
  });

  it("navigates to data summary, export and account closure", () => {
    (usePrivacy as jest.Mock).mockReturnValue(baseHookReturn());
    renderScreen();
    fireEvent.press(screen.getByText("Data summary"));
    expect(mockNavigate).toHaveBeenCalledWith("DataSummary");
    fireEvent.press(screen.getByText("Download my data"));
    expect(mockNavigate).toHaveBeenCalledWith("VoluntaryDataExport");
    fireEvent.press(screen.getByText("Account closure"));
    expect(mockNavigate).toHaveBeenCalledWith("AccountClosureRequest");
  });

  it("shows the information and retention banners", () => {
    (usePrivacy as jest.Mock).mockReturnValue(baseHookReturn());
    renderScreen();
    expect(screen.getByText("Privacy requests are reviewed across every Fuvay category linked to your account.")).toBeTruthy();
    expect(screen.getByText("Active jobs, disputes, finance records and legal retention may affect erasure or closure.")).toBeTruthy();
  });

  it("never shows a Language row (single-language app policy)", () => {
    (usePrivacy as jest.Mock).mockReturnValue(baseHookReturn());
    renderScreen();
    expect(screen.queryByText("Language")).toBeNull();
  });

  it("shows an offline banner", () => {
    (useNetworkStatus as jest.Mock).mockReturnValue({ meta: { readiness: "production_ready" }, networkState: "offline", cacheState: "fresh", pendingDrafts: 0, syncState: "idle" });
    (usePrivacy as jest.Mock).mockReturnValue(baseHookReturn());
    renderScreen();
    expect(screen.getByText("Offline")).toBeTruthy();
  });

  it("shows a loading skeleton, then an error state on failure", () => {
    (usePrivacy as jest.Mock).mockReturnValue(baseHookReturn({ summary: undefined, summaryLoading: true }));
    const { rerender } = renderScreen();
    expect(screen.queryByText("Your privacy settings")).toBeNull();

    (usePrivacy as jest.Mock).mockReturnValue(baseHookReturn({ summary: undefined, summaryLoading: false, summaryIsError: true, summaryError: { code: "VALIDATION_ERROR", category: "network", safeMessage: "Network error", retryable: true } }));
    rerender(<ThemeProvider><PrivacyAndDataScreen route={route} navigation={navigation} /></ThemeProvider>);
    expect(screen.getByText("Couldn't load privacy settings")).toBeTruthy();
  });
});
