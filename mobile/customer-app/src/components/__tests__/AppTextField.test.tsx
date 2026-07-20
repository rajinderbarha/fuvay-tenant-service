import React from "react";
import { fireEvent } from "@testing-library/react-native";
import { AppTextField } from "../forms/AppTextField";
import { renderWithTheme } from "../../testing/render-with-theme";

describe("AppTextField", () => {
  it("renders the label as real text, not only a placeholder", () => {
    const { getByText } = renderWithTheme(<AppTextField label="Full name" value="" onChangeText={() => {}} placeholder="Jane Doe" />);
    expect(getByText("Full name")).toBeTruthy();
  });

  it("calls onChangeText as the user types", () => {
    const onChangeText = jest.fn();
    const { getByDisplayValue } = renderWithTheme(<AppTextField label="Full name" value="J" onChangeText={onChangeText} />);
    fireEvent.changeText(getByDisplayValue("J"), "Jane");
    expect(onChangeText).toHaveBeenCalledWith("Jane");
  });

  it("shows the error message and marks the input invalid", () => {
    const { getByText, getByDisplayValue } = renderWithTheme(
      <AppTextField label="Email" value="bad" onChangeText={() => {}} errorText="Enter a valid email" />
    );
    expect(getByText("Enter a valid email")).toBeTruthy();
    expect(getByDisplayValue("bad").props["aria-invalid"]).toBe(true);
  });

  it("is not editable when disabled", () => {
    const { getByDisplayValue } = renderWithTheme(<AppTextField label="Email" value="x" onChangeText={() => {}} disabled />);
    expect(getByDisplayValue("x").props.editable).toBe(false);
  });
});
