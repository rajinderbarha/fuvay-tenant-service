import React from "react";
import { screen } from "@testing-library/react-native";
import { renderWithTheme as render } from "../../testUtils/renderWithTheme";
import { ProfileScreen } from "../ProfileScreen";

jest.mock("../../context/AuthContext", () => ({
  useAuth: () => ({
    user: { id:"staff-1", full_name:"Test Tech", email:"tech@example.com", specialisations:[], status:"active" },
    logout: jest.fn(),
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
