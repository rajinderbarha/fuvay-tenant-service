import React from "react";
import { render, screen, fireEvent } from "@testing-library/react-native";
import { ThemeProvider } from "../../../design-system/themes";
import { ProfileScreen } from "../ProfileScreen";
import { ProfileDetailDTO } from "../../../services/profile/types";

jest.mock("../useProfile");
jest.mock("../../../hooks/useNetworkStatus", () => ({ useNetworkStatus: jest.fn(() => "online") }));
jest.mock("../../../services/auth/sessionManager", () => ({ revokeCurrentSession: jest.fn(async () => {}) }));

import { useProfile } from "../useProfile";
import { useNetworkStatus } from "../../../hooks/useNetworkStatus";
import { revokeCurrentSession } from "../../../services/auth/sessionManager";

const mockNavigate = jest.fn();
const navigation = { navigate: mockNavigate, goBack: jest.fn() } as any;
const route = { params: undefined } as any;

const BASE_PROFILE: ProfileDetailDTO = {
  identity: { user_id: "u1", full_name: "Priya Sharma", photo_url: null, masked_mobile: "••••• 43210", email_verified: true, mobile_verified: true, status: "active" },
  employment: { tenant_id: "t1", business_name: "QuickFix Services", staff_type: "technician", designation: "Senior Technician", joined_at: "2025-01-01T00:00:00Z", assigned_service_count: 3, staff_reference: "STF-100" },
  readiness: { profile_percentage: 92, completed: 3, required: 4, verified_documents: 2, required_documents: 3, account_verified: true, missing: [{ code: "DOCUMENTS_INCOMPLETE", label: "Upload certification", destination: "documents" }] },
  documents: [],
  required_document_types: ["identity_document", "address_proof", "certification"],
  security: { mfa_enabled: true, active_session_count: 2 },
};

function baseHookReturn(overrides: Partial<ReturnType<typeof useProfile>> = {}) {
  return {
    data: BASE_PROFILE, isLoading: false, isError: false, error: null, isRefetching: false, refetch: jest.fn(),
    mutating: false, mutationError: null, submitDocument: jest.fn(async () => ({ ok: true as const })),
    ...overrides,
  };
}

function renderScreen() {
  return render(<ThemeProvider><ProfileScreen route={route} navigation={navigation} /></ThemeProvider>);
}

beforeEach(() => {
  jest.clearAllMocks();
  (useNetworkStatus as jest.Mock).mockReturnValue("online");
});

describe("ProfileScreen — identity, readiness and menu (Phase R spec sections 3-6)", () => {
  it("renders the identity card with masked mobile, no fabricated fields", () => {
    (useProfile as jest.Mock).mockReturnValue(baseHookReturn());
    renderScreen();
    expect(screen.getByText("Priya Sharma")).toBeTruthy();
    expect(screen.getByText("Senior Technician")).toBeTruthy();
    expect(screen.getByText("QuickFix Services")).toBeTruthy();
    expect(screen.getByText("••••• 43210")).toBeTruthy();
    expect(screen.getByText("Active")).toBeTruthy();
  });

  it("renders the backend-calculated readiness strip", () => {
    (useProfile as jest.Mock).mockReturnValue(baseHookReturn());
    renderScreen();
    expect(screen.getByText("Profile 92%")).toBeTruthy();
    expect(screen.getByText("Documents 2/3")).toBeTruthy();
    expect(screen.getByText("Account verified")).toBeTruthy();
  });

  it("never renders a Language row (explicit instruction: single-language app)", () => {
    (useProfile as jest.Mock).mockReturnValue(baseHookReturn());
    renderScreen();
    expect(screen.queryByText("Language")).toBeNull();
    expect(screen.queryByText("English")).toBeNull();
  });

  it("navigates to each sub-screen from its menu row", () => {
    (useProfile as jest.Mock).mockReturnValue(baseHookReturn());
    renderScreen();
    fireEvent.press(screen.getByText("Employment details"));
    expect(mockNavigate).toHaveBeenCalledWith("EmploymentDetails");
    fireEvent.press(screen.getByText("Documents"));
    expect(mockNavigate).toHaveBeenCalledWith("Documents");
    fireEvent.press(screen.getByText("Active sessions"));
    expect(mockNavigate).toHaveBeenCalledWith("ActiveSessions");
  });

  it("confirms before signing out, then revokes the current session", async () => {
    (useProfile as jest.Mock).mockReturnValue(baseHookReturn());
    renderScreen();
    fireEvent.press(screen.getByText("Sign out"));
    const signOutButtons = await screen.findAllByText("Sign out");
    fireEvent.press(signOutButtons[signOutButtons.length - 1]);
    expect(revokeCurrentSession).toHaveBeenCalled();
  });

  it("shows a loading skeleton while fetching", () => {
    (useProfile as jest.Mock).mockReturnValue(baseHookReturn({ data: undefined, isLoading: true }));
    renderScreen();
    expect(screen.queryByText("Priya Sharma")).toBeNull();
  });

  it("shows an error state when the profile fails to load", () => {
    (useProfile as jest.Mock).mockReturnValue(baseHookReturn({ data: undefined, isLoading: false, isError: true, error: { code: "VALIDATION_ERROR", category: "network", safeMessage: "Network error", retryable: true } }));
    renderScreen();
    expect(screen.getByText("Couldn't load your profile")).toBeTruthy();
  });
});
