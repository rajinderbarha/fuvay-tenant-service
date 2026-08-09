import React from "react";
import { TextInput } from "react-native";
import { renderWithProviders } from "../../testing/renderWithProviders";
import { AppInput } from "../AppInput";

describe("AppInput", () => {
  it("forwards its ref to the underlying TextInput", () => {
    // Load-bearing, not a convenience: a focused input inside a Modal keeps the
    // keyboard up when the Modal unmounts, and only blurring the input itself
    // releases it. LocationPickerModal depends on this to put the ZIP number pad
    // away -- without the forwarded ref the keyboard survives closing the sheet.
    const ref = React.createRef<TextInput>();
    renderWithProviders(<AppInput ref={ref} label="ZIP code" accessibilityLabel="ZIP code" />);

    expect(ref.current).not.toBeNull();
    expect(typeof ref.current?.blur).toBe("function");
  });

  it("still renders its label and error caption", () => {
    const { getByText } = renderWithProviders(
      <AppInput label="ZIP code" error="Enter a valid 6-digit PIN code." />,
    );
    expect(getByText("ZIP code")).toBeTruthy();
    expect(getByText("Enter a valid 6-digit PIN code.")).toBeTruthy();
  });
});
