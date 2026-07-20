import React from "react";
import { screen } from "@testing-library/react-native";
import { renderWithTheme as render } from "../../../testUtils/renderWithTheme";
import { StaffHomeScreen } from "../StaffHomeScreen";
import { StaffWorkQueueScreen } from "../StaffWorkQueueScreen";

jest.mock("../../../context/AuthContext", () => ({
  useAuth: () => ({ user: { id:"s1", full_name:"Staff One", specialisations:[], status:"active" } }),
}));

// UX-05B item 8 regression: StaffHomeScreen/StaffWorkQueueScreen are wired
// into production navigation (StaffTabNavigator, real "staff"-role users
// can reach them) -- unlike the dev-only ux05/*ShowcaseScreen.tsx routes,
// they must never leak the raw internal MOCK_DESIGN_ONLY/API_CONTRACT_REQUIRED
// readiness tokens as user-facing copy, same lesson as FIX 2.
describe("StaffHomeScreen / StaffWorkQueueScreen -- honest, non-jargon copy", () => {
  it("StaffHomeScreen never renders raw readiness tokens", () => {
    render(<StaffHomeScreen />);
    expect(screen.queryByText(/MOCK_DESIGN_ONLY/)).toBeNull();
    expect(screen.queryByText(/API_CONTRACT_REQUIRED/)).toBeNull();
    expect(screen.getByText(/coming soon/i)).toBeTruthy();
  });

  it("StaffWorkQueueScreen never renders raw readiness tokens", () => {
    render(<StaffWorkQueueScreen />);
    expect(screen.queryByText(/MOCK_DESIGN_ONLY/)).toBeNull();
    expect(screen.queryByText(/API_CONTRACT_REQUIRED/)).toBeNull();
    expect(screen.getByText(/coming soon/i)).toBeTruthy();
  });
});
