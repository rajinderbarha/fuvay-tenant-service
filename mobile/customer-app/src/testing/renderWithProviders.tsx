import React from "react";
import { render, RenderOptions } from "@testing-library/react-native";
import { AppProviders } from "../providers/AppProviders";

/** Shared test wrapper -- renders a subtree inside the same provider
 * composition the real app uses, so component tests exercise real theme/
 * query-client wiring instead of a fake stand-in. */
export function renderWithProviders(ui: React.ReactElement, options?: RenderOptions) {
  return render(<AppProviders>{ui}</AppProviders>, options);
}
