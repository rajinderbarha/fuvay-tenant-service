import React from "react";
import { fireEvent } from "@testing-library/react-native";
import { AppIconButton } from "../primitives/AppIconButton";
import { renderWithTheme } from "../../testing/render-with-theme";

describe("AppIconButton", () => {
  it("requires and exposes an accessibility label", () => {
    const { getByLabelText } = renderWithTheme(<AppIconButton icon="close" accessibilityLabel="Close dialog" onPress={() => {}} />);
    expect(getByLabelText("Close dialog")).toBeTruthy();
  });

  it("fires onPress", () => {
    const onPress = jest.fn();
    const { getByLabelText } = renderWithTheme(<AppIconButton icon="close" accessibilityLabel="Close dialog" onPress={onPress} />);
    fireEvent.press(getByLabelText("Close dialog"));
    expect(onPress).toHaveBeenCalledTimes(1);
  });

  it("does not fire onPress when disabled", () => {
    const onPress = jest.fn();
    const { getByLabelText } = renderWithTheme(<AppIconButton icon="close" accessibilityLabel="Close dialog" onPress={onPress} disabled />);
    fireEvent.press(getByLabelText("Close dialog"));
    expect(onPress).not.toHaveBeenCalled();
  });
});
