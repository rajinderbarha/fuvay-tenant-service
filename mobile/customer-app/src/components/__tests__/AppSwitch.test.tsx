import React from "react";
import { fireEvent } from "@testing-library/react-native";
import { AppSwitch } from "../forms/AppSwitch";
import { renderWithTheme } from "../../testing/render-with-theme";

describe("AppSwitch", () => {
  it("exposes the switch role and checked state", () => {
    const { getByRole } = renderWithTheme(<AppSwitch value onValueChange={() => {}} label="Enable notifications" />);
    expect(getByRole("switch").props.accessibilityState.checked).toBe(true);
  });

  it("calls onValueChange with the new value", () => {
    const onValueChange = jest.fn();
    const { getByRole } = renderWithTheme(<AppSwitch value={false} onValueChange={onValueChange} label="Enable notifications" />);
    fireEvent(getByRole("switch"), "valueChange", true);
    expect(onValueChange).toHaveBeenCalledWith(true);
  });

  it("announces disabled state", () => {
    const { getByRole } = renderWithTheme(<AppSwitch value={false} onValueChange={() => {}} label="Enable notifications" disabled />);
    expect(getByRole("switch").props.accessibilityState.disabled).toBe(true);
  });
});
