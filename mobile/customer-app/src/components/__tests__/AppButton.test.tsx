import React from "react";
import { fireEvent, waitFor } from "@testing-library/react-native";
import { renderWithProviders } from "../../testing/renderWithProviders";
import { AppButton } from "../AppButton";

describe("AppButton", () => {
  it("calls onPress when tapped", () => {
    const onPress = jest.fn();
    const { getByRole } = renderWithProviders(<AppButton label="Continue" onPress={onPress} />);
    fireEvent.press(getByRole("button", { name: "Continue" }));
    expect(onPress).toHaveBeenCalledTimes(1);
  });

  it("does not call onPress when disabled", () => {
    const onPress = jest.fn();
    const { getByRole } = renderWithProviders(<AppButton label="Continue" onPress={onPress} disabled />);
    fireEvent.press(getByRole("button", { name: "Continue" }));
    expect(onPress).not.toHaveBeenCalled();
  });

  it("shows a disabled reason when provided", () => {
    const { getByText } = renderWithProviders(
      <AppButton label="Submit" onPress={() => {}} disabled disabledReason="Fill in required fields" />,
    );
    expect(getByText("Fill in required fields")).toBeTruthy();
  });

  it("guards against a second tap while an async onPress is in flight", async () => {
    let resolvePromise: () => void = () => {};
    const onPress = jest.fn(
      () => new Promise<void>(resolve => { resolvePromise = resolve; }),
    );
    const { getByRole } = renderWithProviders(<AppButton label="Save" onPress={onPress} />);
    const button = getByRole("button", { name: "Save" });

    fireEvent.press(button);
    fireEvent.press(button);
    expect(onPress).toHaveBeenCalledTimes(1);

    resolvePromise();
    await waitFor(() => expect(button.props.accessibilityState.busy).toBe(false));
  });
});
