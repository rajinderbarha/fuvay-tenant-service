import React from "react";
import { render, waitFor } from "@testing-library/react-native";
import App from "../App";

jest.mock("../../api/appConfig/publicAppConfig", () => ({
  loadCustomerPublicAppConfig: jest.fn().mockResolvedValue({
    minimumSupportedVersion: "1.0.0",
    storeUrl: null,
    maintenance: false,
    enabledVerticals: ["home_services"],
  }),
  isVersionBelow: jest.fn().mockReturnValue(false),
  getCustomerStoreUrl: jest.fn().mockReturnValue(null),
}));

describe("App entry", () => {
  it("renders the provider composition and navigation shell without crashing, reaching the welcome screen", async () => {
    const { getByLabelText } = render(<App />);
    // Bootstrap resolves once session restoration completes (Phase F);
    // with no stored session, this always lands on the interactive welcome screen.
    await waitFor(() => expect(getByLabelText("Continue to Fuvay sign in")).toBeTruthy());
  });
});
