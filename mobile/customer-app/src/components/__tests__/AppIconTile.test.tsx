import React from "react";
import { fireEvent } from "@testing-library/react-native";

import { renderWithProviders } from "../../testing/renderWithProviders";
import { AppIconTile } from "../AppIconTile";

describe("AppIconTile", () => {
  it("exposes an accessible action when interactive", () => {
    const onPress = jest.fn();
    const { getByRole } = renderWithProviders(
      <AppIconTile name="home-outline" onPress={onPress} accessibilityLabel="Open home services" />,
    );
    fireEvent.press(getByRole("button", { name: "Open home services" }));
    expect(onPress).toHaveBeenCalledTimes(1);
  });

  it("renders non-interactive decorative tiles without a fake button role", () => {
    const { queryByRole } = renderWithProviders(<AppIconTile name="tools" tone="warning" />);
    expect(queryByRole("button")).toBeNull();
  });
});

