import React from "react";
import { Alert, Platform } from "react-native";
import { screen, fireEvent } from "@testing-library/react-native";
import { renderWithTheme as render } from "../../testUtils/renderWithTheme";
import { ProfileScreen } from "../ProfileScreen";

const mockLogout = jest.fn();
jest.mock("../../context/AuthContext", () => ({
  useAuth: () => ({
    user: { id:"staff-1", full_name:"Test Tech", email:"tech@example.com", specialisations:[], status:"active" },
    logout: mockLogout,
  }),
}));

jest.mock("../../hooks/useApi", () => ({
  useApi: () => ({ data:null, loading:false, error:null, refetch:jest.fn() }),
}));

// UX-05B FIX 2 regression: ProfileScreen previously rendered raw
// "MOCK_DESIGN_ONLY -- ..." internal readiness-state strings directly to
// the technician (Assigned Areas/Certifications block, Recent Activity
// block). Those must read as plain, honest copy -- never the raw token.
describe("ProfileScreen", () => {
  it("never renders the raw MOCK_DESIGN_ONLY token to the user", () => {
    render(<ProfileScreen />);
    expect(screen.queryByText(/MOCK_DESIGN_ONLY/)).toBeNull();
  });

  it("shows human-readable copy for the not-yet-available areas/certifications block", () => {
    render(<ProfileScreen />);
    expect(screen.getByText(/aren't tracked here yet/i)).toBeTruthy();
  });
});

// UX-05C real regression: Alert.alert has no react-native-web
// implementation -- Sign Out previously routed through Alert.alert
// unconditionally, which silently no-op'd on the web build (confirmed live
// via headless Chromium: tapping Sign Out fired zero /v1/auth/logout
// requests and left the session token in localStorage). Fixed with a
// Platform.OS branch to window.confirm on web, keeping the original
// Alert.alert flow on native.
describe("ProfileScreen -- Sign Out platform branch", () => {
  const originalOS = Platform.OS;
  afterEach(() => {
    Object.defineProperty(Platform, "OS", { get: () => originalOS });
    mockLogout.mockClear();
  });

  it("on web: uses window.confirm (real on react-native-web) and calls logout when confirmed", () => {
    Object.defineProperty(Platform, "OS", { get: () => "web" });
    (global as unknown as { window: { confirm: jest.Mock } }).window = { confirm: jest.fn().mockReturnValue(true) };
    const confirmSpy = (global as unknown as { window: { confirm: jest.Mock } }).window.confirm;
    render(<ProfileScreen />);
    fireEvent.press(screen.getByText("Sign Out"));
    expect(confirmSpy).toHaveBeenCalled();
    expect(mockLogout).toHaveBeenCalledTimes(1);
  });

  it("on web: does not call logout when window.confirm is cancelled", () => {
    Object.defineProperty(Platform, "OS", { get: () => "web" });
    (global as unknown as { window: { confirm: jest.Mock } }).window = { confirm: jest.fn().mockReturnValue(false) };
    render(<ProfileScreen />);
    fireEvent.press(screen.getByText("Sign Out"));
    expect(mockLogout).not.toHaveBeenCalled();
  });

  it("on native (ios/android): still uses the original Alert.alert confirmation flow", () => {
    Object.defineProperty(Platform, "OS", { get: () => "ios" });
    const alertSpy = jest.spyOn(Alert, "alert").mockImplementation((title, msg, buttons) => {
      const signOutButton = buttons?.find(b => b.text === "Sign Out");
      signOutButton?.onPress?.();
    });
    render(<ProfileScreen />);
    fireEvent.press(screen.getByText("Sign Out"));
    expect(alertSpy).toHaveBeenCalled();
    expect(mockLogout).toHaveBeenCalledTimes(1);
    alertSpy.mockRestore();
  });
});
