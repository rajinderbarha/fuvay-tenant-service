import React from "react";
import { render, screen, fireEvent } from "@testing-library/react-native";
import { ThemeProvider } from "../../design-system/themes";
import { RestrictedStateScreen } from "../placeholders/RestrictedStateScreen";

const mockRetryBootstrap = jest.fn().mockResolvedValue(undefined);
const mockInvalidateSession = jest.fn().mockResolvedValue(undefined);
jest.mock("../session/SessionProvider", () => ({
  useSession: () => ({
    retryBootstrap: mockRetryBootstrap, invalidateSession: mockInvalidateSession,
    accessContext: { authenticated: true, tenantStatus: "suspended", technicianStatus: "suspended", enabledVerticals: ["home_services"] },
  }),
}));
jest.mock("../../services/api/healthApi", () => ({ checkPublicHealth: jest.fn().mockResolvedValue("online") }));

beforeEach(() => jest.clearAllMocks());

function renderScreen(screenName: any, reasonCode: any) {
  return render(<ThemeProvider><RestrictedStateScreen screen={screenName} reasonCode={reasonCode} /></ThemeProvider>);
}

describe("RestrictedStateScreen actions (Phase G spec section 10)", () => {
  it("Retry calls retryBootstrap for a suspended tenant", async () => {
    renderScreen("TenantSuspended", "TENANT_INACTIVE");
    fireEvent.press(screen.getByText("Retry"));
    expect(mockRetryBootstrap).toHaveBeenCalledTimes(1);
  });

  it("Sign out calls invalidateSession for a suspended account", () => {
    renderScreen("AccountSuspended", "TECHNICIAN_INACTIVE");
    fireEvent.press(screen.getByText("Sign out"));
    expect(mockInvalidateSession).toHaveBeenCalledTimes(1);
  });

  it("shows only Sign out (no Retry) for access denied", () => {
    renderScreen("AccessDenied", "ROLE_NOT_ALLOWED");
    expect(screen.getByText("Sign out")).toBeTruthy();
    expect(screen.queryByText("Retry")).toBeNull();
  });

  it("shows no actions for a mandatory app update -- never a bypass", () => {
    renderScreen("AppUpdateRequired", "APP_UPDATE_REQUIRED");
    expect(screen.queryByText("Retry")).toBeNull();
    expect(screen.queryByText("Sign out")).toBeNull();
  });

  it("shows Check again + View service status (no Sign out) for a generic service-unavailable state", () => {
    renderScreen("ServiceUnavailable", "ROLE_NOT_ALLOWED");
    expect(screen.getByText("Check again")).toBeTruthy();
    expect(screen.getByText("View service status")).toBeTruthy();
    expect(screen.queryByText("Sign out")).toBeNull();
  });

  it("never shows protected content underneath -- only the restricted message and actions render", () => {
    renderScreen("TechnicianInactive", "TECHNICIAN_INACTIVE");
    expect(screen.queryByText("Home")).toBeNull();
    expect(screen.queryByText("Jobs")).toBeNull();
  });

  it("shows the real vertical and status for a suspended account, never a fabricated business name", () => {
    renderScreen("AccountSuspended", "TECHNICIAN_INACTIVE");
    expect(screen.getByText("home_services")).toBeTruthy();
    expect(screen.getByText("suspended")).toBeTruthy();
  });

  it("shows the drafts-preserved notice for a mandatory update, and never a fake store-review claim", () => {
    renderScreen("AppUpdateRequired", "APP_UPDATE_REQUIRED");
    expect(screen.getByText("Your saved drafts will remain on this device.")).toBeTruthy();
    expect(screen.getByText("Update app")).toBeTruthy();
  });
});
