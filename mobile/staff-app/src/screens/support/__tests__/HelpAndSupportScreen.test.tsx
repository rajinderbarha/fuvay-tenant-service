import React from "react";
import { render, screen, fireEvent } from "@testing-library/react-native";
import { ThemeProvider } from "../../../design-system/themes";
import { HelpAndSupportScreen } from "../HelpAndSupportScreen";
import { HelpWorkspaceDTO } from "../../../services/support/types";

jest.mock("../useHelpWorkspace");
jest.mock("../../../hooks/useNetworkStatus", () => ({ useNetworkStatus: jest.fn(() => "online") }));

import { useHelpWorkspace } from "../useHelpWorkspace";
import { useNetworkStatus } from "../../../hooks/useNetworkStatus";

const mockNavigate = jest.fn();
const navigation = { navigate: mockNavigate, goBack: jest.fn() } as any;
const route = { params: undefined } as any;

const WORKSPACE: HelpWorkspaceDTO = {
  service_status: { state: "operational", message: "All good", last_checked_at: null, evidence_fresh: true, affected_components: [], active_incident_count: 0 },
  summary: { open: 1, awaiting_your_reply: 0, resolved: 2, total: 3 },
  requests: [{
    id: "req-1", ticket_number: "SUP-2026-0184", subject: "Job photo upload failed", category: "technical",
    category_label: "Technical issue", status: "waiting_for_serviceos", status_label: "In progress",
    impact: "one_user_affected", impact_label: "One user affected", sla_display: "On track",
    created_at: "2026-07-29T00:00:00Z", updated_at: "2026-07-31T09:12:00Z",
  }],
  requests_total: 1,
  quick_help: [{ key: "bookings_jobs", label: "Bookings & jobs", icon: "wrench", description: "", article_count: 3, has_content: true }],
  recommended_articles: [], knowledge_total: 3,
  form_options: { categories: [], impacts: [] },
  permissions: { can_view: true, can_create: true, can_reply: true, can_reopen: false },
};

function baseHookReturn(overrides: Partial<ReturnType<typeof useHelpWorkspace>> = {}) {
  return {
    data: WORKSPACE, isLoading: false, isError: false, error: null, isRefetching: false, refetch: jest.fn(),
    manager: { display_name: "Rajiv Kumar", designation: "Service Manager" }, invalidate: jest.fn(),
    ...overrides,
  };
}

function renderScreen() {
  return render(<ThemeProvider><HelpAndSupportScreen route={route} navigation={navigation} /></ThemeProvider>);
}

beforeEach(() => {
  jest.clearAllMocks();
  (useNetworkStatus as jest.Mock).mockReturnValue("online");
});

describe("HelpAndSupportScreen (Phase Y)", () => {
  it("renders the intro card and quick-help tiles", () => {
    (useHelpWorkspace as jest.Mock).mockReturnValue(baseHookReturn());
    renderScreen();
    expect(screen.getByText("How can we help?")).toBeTruthy();
    expect(screen.getByText("Job execution")).toBeTruthy();
    expect(screen.getByText("Schedule & leave")).toBeTruthy();
    expect(screen.getByText("Account & security")).toBeTruthy();
    expect(screen.getByText("Documents")).toBeTruthy();
  });

  it("shows the real manager name on Contact your manager", () => {
    (useHelpWorkspace as jest.Mock).mockReturnValue(baseHookReturn());
    renderScreen();
    expect(screen.getByText("Rajiv Kumar")).toBeTruthy();
  });

  it("routes contact-support rows with the correct intent", () => {
    (useHelpWorkspace as jest.Mock).mockReturnValue(baseHookReturn());
    renderScreen();
    fireEvent.press(screen.getByText("Contact your manager"));
    expect(mockNavigate).toHaveBeenCalledWith("CreateSupportRequest", { intent: "manager" });
    fireEvent.press(screen.getByText("ServiceOS support"));
    expect(mockNavigate).toHaveBeenCalledWith("CreateSupportRequest", { intent: "platform" });
    fireEvent.press(screen.getByText("Report a technical problem"));
    expect(mockNavigate).toHaveBeenCalledWith("CreateSupportRequest", { intent: "technical" });
  });

  it("shows the recent request and navigates to its detail", () => {
    (useHelpWorkspace as jest.Mock).mockReturnValue(baseHookReturn());
    renderScreen();
    expect(screen.getByText("SUP-2026-0184")).toBeTruthy();
    fireEvent.press(screen.getByText("View request"));
    expect(mockNavigate).toHaveBeenCalledWith("SupportRequestDetail", { requestId: "req-1" });
  });

  it("shows the real backend-derived service status, never a fabricated claim", () => {
    (useHelpWorkspace as jest.Mock).mockReturnValue(baseHookReturn());
    renderScreen();
    expect(screen.getByText("All systems operational")).toBeTruthy();
  });

  it("shows the emergency notice, never a 24/7 promise", () => {
    (useHelpWorkspace as jest.Mock).mockReturnValue(baseHookReturn());
    renderScreen();
    expect(screen.getByText(/For emergencies, contact local emergency services/)).toBeTruthy();
    expect(screen.queryByText(/24\/7/)).toBeNull();
  });

  it("never shows a Language row (single-language app policy)", () => {
    (useHelpWorkspace as jest.Mock).mockReturnValue(baseHookReturn());
    renderScreen();
    expect(screen.queryByText("Language")).toBeNull();
  });

  it("shows an offline banner", () => {
    (useNetworkStatus as jest.Mock).mockReturnValue("offline");
    (useHelpWorkspace as jest.Mock).mockReturnValue(baseHookReturn());
    renderScreen();
    expect(screen.getByText("Offline")).toBeTruthy();
  });

  it("shows a loading skeleton, then an error state on failure", () => {
    (useHelpWorkspace as jest.Mock).mockReturnValue(baseHookReturn({ data: undefined, isLoading: true }));
    const { rerender } = renderScreen();
    expect(screen.queryByText("How can we help?")).toBeNull();

    (useHelpWorkspace as jest.Mock).mockReturnValue(baseHookReturn({ data: undefined, isLoading: false, isError: true, error: { code: "VALIDATION_ERROR", category: "network", safeMessage: "Network error", retryable: true } }));
    rerender(<ThemeProvider><HelpAndSupportScreen route={route} navigation={navigation} /></ThemeProvider>);
    expect(screen.getByText("Couldn't load help & support")).toBeTruthy();
  });
});
