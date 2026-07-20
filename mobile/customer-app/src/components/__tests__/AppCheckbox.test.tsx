import React from "react";
import { fireEvent } from "@testing-library/react-native";
import { AppCheckbox } from "../forms/AppCheckbox";
import { renderWithTheme } from "../../testing/render-with-theme";

describe("AppCheckbox", () => {
  it("exposes the checkbox role and checked state", () => {
    const { getByRole } = renderWithTheme(<AppCheckbox checked onChange={() => {}} label="Agree to terms" />);
    expect(getByRole("checkbox").props.accessibilityState.checked).toBe(true);
  });

  it("toggles on press", () => {
    const onChange = jest.fn();
    const { getByRole } = renderWithTheme(<AppCheckbox checked={false} onChange={onChange} label="Agree to terms" />);
    fireEvent.press(getByRole("checkbox"));
    expect(onChange).toHaveBeenCalledWith(true);
  });

  it("does not toggle when disabled", () => {
    const onChange = jest.fn();
    const { getByRole } = renderWithTheme(<AppCheckbox checked={false} onChange={onChange} label="Agree to terms" disabled />);
    fireEvent.press(getByRole("checkbox"));
    expect(onChange).not.toHaveBeenCalled();
  });

  it("represents an indeterminate state as mixed", () => {
    const { getByRole } = renderWithTheme(<AppCheckbox checked="indeterminate" onChange={() => {}} label="Select all" />);
    expect(getByRole("checkbox").props.accessibilityState.checked).toBe("mixed");
  });
});
