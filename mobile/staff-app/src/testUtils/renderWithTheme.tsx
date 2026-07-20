import React from "react";
import { render, type RenderOptions } from "@testing-library/react-native";
import { ThemeProvider } from "../context/ThemeContext";

/**
 * UX-05 Round 5: shared RNTL render helper -- most ux05 components now call
 * useAppTheme() and require a ThemeProvider ancestor. Centralized here so
 * every test file doesn't reimplement the same wrapper.
 */
export function renderWithTheme(ui: React.ReactElement, options?: RenderOptions) {
  return render(<ThemeProvider>{ui}</ThemeProvider>, options);
}
