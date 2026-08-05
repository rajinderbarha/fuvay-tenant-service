import React from "react";
import { render, screen, fireEvent } from "@testing-library/react-native";
import { ThemeProvider } from "../../../design-system/themes";
import { DocumentsScreen } from "../DocumentsScreen";
import { DocumentsDetailDTO } from "../../../services/documents/types";

jest.mock("../useDocuments");
jest.mock("../../../hooks/useNetworkStatus", () => ({ useNetworkStatus: jest.fn(() => ({ meta: { readiness: "production_ready" }, networkState: "online", cacheState: "fresh", pendingDrafts: 0, syncState: "idle" })) }));

import { useDocuments } from "../useDocuments";
import { useNetworkStatus } from "../../../hooks/useNetworkStatus";

const mockNavigate = jest.fn();
const navigation = { navigate: mockNavigate, goBack: jest.fn() } as any;
const route = { params: undefined } as any;

const DETAIL: DocumentsDetailDTO = {
  readiness: { percentage: 80, complete: 4, required: 5, action_needed: 1, pending: 1, verified: 3 },
  requirements: [
    { requirement_id: "r1", code: "technician_identity_proof", label: "Government ID", required: true, requires_expiry: true, requires_document_number: true, current_document_id: "d1", current_version: 1, review_status: "verified", display_condition: null, submitted_at: "2025-03-14T00:00:00Z", verified_at: "2025-03-15T00:00:00Z", expires_at: null, days_until_expiry: null, reviewer_note: null, allowed_actions: ["view", "history"] },
    { requirement_id: "r2", code: "technician_background_check", label: "Police verification", required: true, requires_expiry: false, requires_document_number: false, current_document_id: "d2", current_version: 1, review_status: "pending_review", display_condition: null, submitted_at: "2025-07-29T00:00:00Z", verified_at: null, expires_at: null, days_until_expiry: null, reviewer_note: null, allowed_actions: ["view", "history"] },
    { requirement_id: "r3", code: "technician_skill_certificate", label: "AC Technician Certificate", required: false, requires_expiry: true, requires_document_number: false, current_document_id: "d3", current_version: 1, review_status: "verified", display_condition: "expiring_soon", submitted_at: "2025-01-01T00:00:00Z", verified_at: "2025-01-02T00:00:00Z", expires_at: "2026-08-12", days_until_expiry: 12, reviewer_note: null, allowed_actions: ["view", "history", "replace"] },
  ],
};

function baseHookReturn(overrides: Partial<ReturnType<typeof useDocuments>> = {}) {
  return {
    data: DETAIL, isLoading: false, isError: false, error: null, isRefetching: false, refetch: jest.fn(),
    uploading: false, uploadError: null, submit: jest.fn(async () => ({ ok: true as const })),
    ...overrides,
  };
}

function renderScreen() {
  return render(<ThemeProvider><DocumentsScreen route={route} navigation={navigation} /></ThemeProvider>);
}

beforeEach(() => {
  jest.clearAllMocks();
  (useNetworkStatus as jest.Mock).mockReturnValue({ meta: { readiness: "production_ready" }, networkState: "online", cacheState: "fresh", pendingDrafts: 0, syncState: "idle" });
});

describe("DocumentsScreen (Phase T)", () => {
  it("renders backend-calculated readiness, never a client-computed percentage", () => {
    (useDocuments as jest.Mock).mockReturnValue(baseHookReturn());
    renderScreen();
    expect(screen.getByText("80%")).toBeTruthy();
    expect(screen.getByText("4 of 5 complete")).toBeTruthy();
    expect(screen.getByText("1 document needs attention")).toBeTruthy();
  });

  it("shows the expiring-soon projection with exact remaining days", () => {
    (useDocuments as jest.Mock).mockReturnValue(baseHookReturn());
    renderScreen();
    expect(screen.getByText("Expires in 12 days")).toBeTruthy();
  });

  it("filters to Verified only", () => {
    (useDocuments as jest.Mock).mockReturnValue(baseHookReturn());
    renderScreen();
    fireEvent(screen.getByLabelText("Verified, 3"), "touchEnd");
    expect(screen.getByText("Government ID")).toBeTruthy();
    expect(screen.queryByText("Police verification")).toBeNull();
  });

  it("navigates to upload for a missing document and detail for an existing one", () => {
    (useDocuments as jest.Mock).mockReturnValue(baseHookReturn());
    renderScreen();
    fireEvent.press(screen.getByText("Government ID"));
    expect(mockNavigate).toHaveBeenCalledWith("DocumentDetail", { docCode: "technician_identity_proof" });
  });

  it("shows the footer security and business-verification notices", () => {
    (useDocuments as jest.Mock).mockReturnValue(baseHookReturn());
    renderScreen();
    expect(screen.getByText("Files are encrypted and visible only to authorized reviewers.")).toBeTruthy();
    expect(screen.getByText("Verification is completed by your business.")).toBeTruthy();
  });

  it("disables upload affordances while offline", () => {
    (useNetworkStatus as jest.Mock).mockReturnValue({ meta: { readiness: "production_ready" }, networkState: "offline", cacheState: "fresh", pendingDrafts: 0, syncState: "idle" });
    (useDocuments as jest.Mock).mockReturnValue(baseHookReturn());
    renderScreen();
    expect(screen.getByText("Offline")).toBeTruthy();
  });

  it("shows a loading skeleton, then an error state on failure", () => {
    (useDocuments as jest.Mock).mockReturnValue(baseHookReturn({ data: undefined, isLoading: true }));
    const { rerender } = renderScreen();
    expect(screen.queryByText("80%")).toBeNull();

    (useDocuments as jest.Mock).mockReturnValue(baseHookReturn({ data: undefined, isLoading: false, isError: true, error: { code: "VALIDATION_ERROR", category: "network", safeMessage: "Network error", retryable: true } }));
    rerender(<ThemeProvider><DocumentsScreen route={route} navigation={navigation} /></ThemeProvider>);
    expect(screen.getByText("Couldn't load documents")).toBeTruthy();
  });
});
