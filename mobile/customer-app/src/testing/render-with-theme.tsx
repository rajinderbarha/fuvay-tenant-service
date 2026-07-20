import React from "react";
import { render, type RenderOptions } from "@testing-library/react-native";
import { ThemeProvider } from "../design-system/themes/theme-provider";

/** Shared test helper — every component under test needs ThemeProvider context. */
export function renderWithTheme(ui: React.ReactElement, options?: RenderOptions) {
  return render(<ThemeProvider>{ui}</ThemeProvider>, options);
}
