import React from "react";
import { render, screen, fireEvent } from "@testing-library/react-native";
import { ThemeProvider } from "../../../design-system/themes";
import { EmploymentDetailsScreen } from "../EmploymentDetailsScreen";
import { EmploymentDetailDTO } from "../../../services/employment/types";

jest.mock("../useEmploymentDetails");
jest.mock("../../../hooks/useNetworkStatus", () => ({ useNetworkStatus: jest.fn(() => ({ meta: { readiness: "production_ready" }, networkState: "online", cacheState: "fresh", pendingDrafts: 0, syncState: "idle" })) }));

import { useEmploymentDetails } from "../useEmploymentDetails";
import { useNetworkStatus } from "../../../hooks/useNetworkStatus";

const mockNavigate = jest.fn();
const navigation = { navigate: mockNavigate, goBack: jest.fn() } as any;
const route = { params: undefined } as any;

const ACTIVE_DETAIL: EmploymentDetailDTO = {
  business: { tenant_id: "t1", name: "Acme Home Services", logo_url: null, vertical_code: "home_services", vertical_label: "Home Services" },
  employment: {
    staff_id: "s1", staff_reference: "TECH-0042", staff_type: "technician", designation: "Senior Technician",
    status: "active", status_known: true, joined_at: "2025-03-12T00:00:00Z",
    reports_to: { display_name: "Rajiv Kumar", designation: "Service Manager" },
  },
  status_known: true,
  assignments: {
    service_groups: [{ id: "g1", code: null, name: "AC & HVAC" }],
    job_types: [{ id: "j1", code: null, name: "Repair" }],
    verified_skills: [
      { id: "sk1", name: "AC diagnostics", verification_status: "verified", verified_at: "2025-04-01T00:00:00Z", expires_at: null },
      { id: "sk2", name: "Gas line repair", verification_status: "pending", verified_at: null, expires_at: null },
    ],
  },
  scope: { service_area_summary: "Ludhiana · 12 km radius", working_schedule_summary: "Mon–Sat · 9:00 AM–6:00 PM", effective_capability_count: 7 },
  permissions: { capability_count: 7, groups: [{ key: "jobs", label: "Jobs", items: ["View assigned jobs"] }, { key: "restricted", label: "Restricted", items: ["Cannot reassign jobs"] }] },
  allowed_actions: { request_correction: true },
};

function baseHookReturn(overrides: Partial<ReturnType<typeof useEmploymentDetails>> = {}) {
  return {
    data: ACTIVE_DETAIL, isLoading: false, isError: false, error: null, isRefetching: false, refetch: jest.fn(),
    corrections: [], correctionsLoading: false,
    submitting: false, submitError: null,
    submitCorrection: jest.fn(async () => ({ ok: true as const })),
    ...overrides,
  };
}

function renderScreen() {
  return render(<ThemeProvider><EmploymentDetailsScreen route={route} navigation={navigation} /></ThemeProvider>);
}

beforeEach(() => {
  jest.clearAllMocks();
  (useNetworkStatus as jest.Mock).mockReturnValue({ meta: { readiness: "production_ready" }, networkState: "online", cacheState: "fresh", pendingDrafts: 0, syncState: "idle" });
});

describe("EmploymentDetailsScreen (Phase S)", () => {
  it("renders business identity, employment fields and assignment chips", () => {
    (useEmploymentDetails as jest.Mock).mockReturnValue(baseHookReturn());
    renderScreen();
    expect(screen.getByText("Acme Home Services")).toBeTruthy();
    expect(screen.getByText("Active")).toBeTruthy();
    expect(screen.getByText("TECH-0042")).toBeTruthy();
    expect(screen.getByText("Senior Technician")).toBeTruthy();
    expect(screen.getByText("Rajiv Kumar · Service Manager")).toBeTruthy();
    expect(screen.getByText("AC & HVAC")).toBeTruthy();
    expect(screen.getByText("Repair")).toBeTruthy();
  });

  it("only marks the genuinely-verified skill, not the pending one", () => {
    (useEmploymentDetails as jest.Mock).mockReturnValue(baseHookReturn());
    renderScreen();
    const verified = screen.getByLabelText("AC diagnostics, verified");
    const pending = screen.getByLabelText("Gas line repair, pending verification");
    expect(verified).toBeTruthy();
    expect(pending).toBeTruthy();
  });

  it("navigates to Availability Preferences when working schedule is tapped", () => {
    (useEmploymentDetails as jest.Mock).mockReturnValue(baseHookReturn());
    renderScreen();
    fireEvent.press(screen.getByText("Working schedule"));
    expect(mockNavigate).toHaveBeenCalledWith("AvailabilityPreferences");
  });

  it("opens the permissions summary sheet without a raw permission-code list as primary UI", () => {
    (useEmploymentDetails as jest.Mock).mockReturnValue(baseHookReturn());
    renderScreen();
    fireEvent.press(screen.getByText("Permissions"));
    expect(screen.getByText("Your permissions")).toBeTruthy();
    expect(screen.getByText("View assigned jobs")).toBeTruthy();
    expect(screen.getByText("Cannot reassign jobs")).toBeTruthy();
  });

  it("shows the tenant-managed footer notice and a Request correction action, never inline edit controls", () => {
    (useEmploymentDetails as jest.Mock).mockReturnValue(baseHookReturn());
    renderScreen();
    expect(screen.getByText("Employment details are managed by Acme Home Services.")).toBeTruthy();
    expect(screen.getByText("Request correction")).toBeTruthy();
  });

  it("hides assigned work and permissions while employment is inactive", () => {
    (useEmploymentDetails as jest.Mock).mockReturnValue(baseHookReturn({
      data: { ...ACTIVE_DETAIL, employment: { ...ACTIVE_DETAIL.employment!, status: "inactive" }, scope: null, permissions: null, assignments: { service_groups: [], job_types: [], verified_skills: [] } },
    }));
    renderScreen();
    expect(screen.getByText("Employment inactive")).toBeTruthy();
    expect(screen.queryByText("AC & HVAC")).toBeNull();
  });

  it("shows an 'unavailable' state rather than assuming active for an unmapped status", () => {
    (useEmploymentDetails as jest.Mock).mockReturnValue(baseHookReturn({
      data: { ...ACTIVE_DETAIL, status_known: false, employment: { ...ACTIVE_DETAIL.employment!, status_known: false } },
    }));
    renderScreen();
    expect(screen.getByText("Employment status unavailable")).toBeTruthy();
  });

  it("shows a loading skeleton, then an error state on failure", () => {
    (useEmploymentDetails as jest.Mock).mockReturnValue(baseHookReturn({ data: undefined, isLoading: true }));
    const { rerender } = renderScreen();
    expect(screen.queryByText("Acme Home Services")).toBeNull();

    (useEmploymentDetails as jest.Mock).mockReturnValue(baseHookReturn({ data: undefined, isLoading: false, isError: true, error: { code: "VALIDATION_ERROR", category: "network", safeMessage: "Network error", retryable: true } }));
    rerender(<ThemeProvider><EmploymentDetailsScreen route={route} navigation={navigation} /></ThemeProvider>);
    expect(screen.getByText("Couldn't load employment details")).toBeTruthy();
  });

  it("shows an offline banner when offline", () => {
    (useNetworkStatus as jest.Mock).mockReturnValue({ meta: { readiness: "production_ready" }, networkState: "offline", cacheState: "fresh", pendingDrafts: 0, syncState: "idle" });
    (useEmploymentDetails as jest.Mock).mockReturnValue(baseHookReturn());
    renderScreen();
    expect(screen.getByText("Offline")).toBeTruthy();
  });
});
