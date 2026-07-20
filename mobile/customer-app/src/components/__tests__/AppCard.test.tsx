import React from "react";
import { Text } from "react-native";
import { fireEvent } from "@testing-library/react-native";
import { AppCard } from "../primitives/AppCard";
import { renderWithTheme } from "../../testing/render-with-theme";

describe("AppCard", () => {
  it("renders children", () => {
    const { getByText } = renderWithTheme(
      <AppCard>
        <Text>Card content</Text>
      </AppCard>
    );
    expect(getByText("Card content")).toBeTruthy();
  });

  it("fires onPress only when variant is interactive", () => {
    const onPress = jest.fn();
    const { getByRole } = renderWithTheme(
      <AppCard variant="interactive" onPress={onPress} accessibilityLabel="Open booking">
        <Text>Card content</Text>
      </AppCard>
    );
    fireEvent.press(getByRole("button"));
    expect(onPress).toHaveBeenCalledTimes(1);
  });

  it("renders as non-interactive when no onPress is provided, even with variant='interactive'", () => {
    const { queryByRole } = renderWithTheme(
      <AppCard variant="interactive">
        <Text>Card content</Text>
      </AppCard>
    );
    expect(queryByRole("button")).toBeNull();
  });
});
