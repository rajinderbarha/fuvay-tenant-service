import React from "react";
import { render, screen } from "@testing-library/react-native";
import { ThemeProvider } from "../../design-system/themes";
import { FoundationSplash } from "../FoundationSplash";

describe("FoundationSplash", () => {
  it("shows a customer-safe session loading state without internal design controls", () => {
    render(
      <ThemeProvider>
        <FoundationSplash />
      </ThemeProvider>,
    );

    expect(screen.getByText("Fuvay Staff")).toBeTruthy();
    expect(screen.getByText("Checking your secure session…")).toBeTruthy();
    expect(screen.getByLabelText("Loading")).toBeTruthy();
    expect(screen.queryByText(/Design foundation preview/i)).toBeNull();
    expect(screen.queryByText("System")).toBeNull();
    expect(screen.queryByText("STATUS TOKEN PREVIEW")).toBeNull();
  });
});
