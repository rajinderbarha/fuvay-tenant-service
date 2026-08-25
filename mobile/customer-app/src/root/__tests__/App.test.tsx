import React from "react";
import { render, waitFor } from "@testing-library/react-native";
import App from "../App";

describe("App entry", () => {
  it("renders the provider composition and navigation shell without crashing, reaching the welcome screen", async () => {
    const { getByLabelText } = render(<App />);
    // Bootstrap resolves once session restoration completes (Phase F);
    // with no stored session, this always lands on the interactive welcome screen.
    await waitFor(() => expect(getByLabelText("Get started with Fuvay")).toBeTruthy());
  });
});
