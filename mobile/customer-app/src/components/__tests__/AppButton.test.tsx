import React from "react";
import { fireEvent } from "@testing-library/react-native";
import { AppButton } from "../primitives/AppButton";
import { renderWithTheme } from "../../testing/render-with-theme";

describe("AppButton", () => {
  it("renders the label and fires onPress", () => {
    const onPress = jest.fn();
    const { getByText } = renderWithTheme(<AppButton label="Continue" onPress={onPress} />);
    fireEvent.press(getByText("Continue"));
    expect(onPress).toHaveBeenCalledTimes(1);
  });

  it("exposes the button accessibility role", () => {
    const { getByRole } = renderWithTheme(<AppButton label="Continue" onPress={() => {}} />);
    expect(getByRole("button")).toBeTruthy();
  });

  it("does not fire onPress when disabled", () => {
    const onPress = jest.fn();
    const { getByRole } = renderWithTheme(<AppButton label="Continue" onPress={onPress} disabled />);
    fireEvent.press(getByRole("button"));
    expect(onPress).not.toHaveBeenCalled();
  });

  it("announces the disabled state to assistive tech", () => {
    const { getByRole } = renderWithTheme(<AppButton label="Continue" onPress={() => {}} disabled />);
    expect(getByRole("button").props.accessibilityState.disabled).toBe(true);
  });

  it("does not fire onPress while loading and announces busy state", () => {
    const onPress = jest.fn();
    const { getByRole } = renderWithTheme(<AppButton label="Continue" onPress={onPress} loading />);
    const button = getByRole("button");
    fireEvent.press(button);
    expect(onPress).not.toHaveBeenCalled();
    expect(button.props.accessibilityState.busy).toBe(true);
  });

  it("requires an accessibility label for icon-only buttons", () => {
    const { getByLabelText } = renderWithTheme(<AppButton label="Add item" variant="icon-only" onPress={() => {}} accessibilityLabel="Add item" />);
    expect(getByLabelText("Add item")).toBeTruthy();
  });

  it("ignores a second rapid press (double-tap protection)", () => {
    const onPress = jest.fn();
    const { getByRole } = renderWithTheme(<AppButton label="Submit" onPress={onPress} />);
    const button = getByRole("button");
    fireEvent.press(button);
    fireEvent.press(button);
    expect(onPress).toHaveBeenCalledTimes(1);
  });
});
