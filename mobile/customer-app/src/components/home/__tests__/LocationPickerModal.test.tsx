import React from "react";
import { Keyboard } from "react-native";
import { fireEvent, waitFor } from "@testing-library/react-native";
import { renderWithProviders } from "../../../testing/renderWithProviders";
import { LocationPickerModal } from "../LocationPickerModal";

describe("LocationPickerModal", () => {
  it("cannot be confirmed with an incomplete ZIP code", () => {
    // The action is disabled rather than answering "enter a valid PIN" -- a button that
    // only ever refuses is a button that does nothing.
    const onConfirm = jest.fn();
    const { getByLabelText, getByText } = renderWithProviders(
      <LocationPickerModal visible currentZipcode={null} onClose={() => {}} onConfirm={onConfirm} />,
    );
    fireEvent.changeText(getByLabelText("ZIP code"), "141");
    fireEvent.press(getByText("Show services here"));
    expect(onConfirm).not.toHaveBeenCalled();
  });

  it("names the action for what it does, first time and after", () => {
    const first = renderWithProviders(
      <LocationPickerModal visible currentZipcode={null} onClose={() => {}} onConfirm={() => {}} />,
    );
    expect(first.getByText("Set your location")).toBeTruthy();
    expect(first.getByText("Show services here")).toBeTruthy();

    const again = renderWithProviders(
      <LocationPickerModal visible currentZipcode="141001" onClose={() => {}} onConfirm={() => {}} />,
    );
    expect(again.getByText("Change location")).toBeTruthy();
    expect(again.getByText("Update location")).toBeTruthy();
  });

  it("confirms a valid 6-digit ZIP and closes", () => {
    const onConfirm = jest.fn();
    const onClose = jest.fn();
    const { getByLabelText, getByText } = renderWithProviders(
      <LocationPickerModal visible currentZipcode={null} onClose={onClose} onConfirm={onConfirm} />,
    );
    fireEvent.changeText(getByLabelText("ZIP code"), "141001");
    fireEvent.press(getByText("Show services here"));
    expect(onConfirm).toHaveBeenCalledWith("141001");
    // Closing is deferred one frame so the blur is processed before the Modal
    // unmounts -- otherwise the keyboard is left behind (see the component).
    return waitFor(() => expect(onClose).toHaveBeenCalledTimes(1));
  });

  it("puts the number pad away on confirm, not just the sheet", async () => {
    // The field lives inside a Modal, and unmounting a focused TextInput with the
    // keyboard up leaves the keyboard on screen -- a number pad covering half of Home
    // with nothing focused to dismiss it by tapping.
    const dismiss = jest.spyOn(Keyboard, "dismiss");
    const onClose = jest.fn();
    const { getByLabelText, getByText } = renderWithProviders(
      <LocationPickerModal visible currentZipcode={null} onClose={onClose} onConfirm={() => {}} />,
    );
    fireEvent.changeText(getByLabelText("ZIP code"), "141001");
    fireEvent.press(getByText("Show services here"));
    expect(dismiss).toHaveBeenCalled();
    await waitFor(() => expect(onClose).toHaveBeenCalledTimes(1));
    dismiss.mockRestore();
  });

  it("puts the number pad away when the sheet is dismissed without confirming", () => {
    const dismiss = jest.spyOn(Keyboard, "dismiss");
    const onClose = jest.fn();
    const { getByLabelText } = renderWithProviders(
      <LocationPickerModal visible currentZipcode={null} onClose={onClose} onConfirm={() => {}} />,
    );
    fireEvent.press(getByLabelText("Close"));
    expect(dismiss).toHaveBeenCalled();
    return waitFor(() => expect(onClose).toHaveBeenCalledTimes(1)).then(() => {
      dismiss.mockRestore();
    });
  });

  it("pre-fills the current ZIP when reopened", () => {
    const { getByLabelText } = renderWithProviders(
      <LocationPickerModal visible currentZipcode="141001" onClose={() => {}} onConfirm={() => {}} />,
    );
    expect(getByLabelText("ZIP code").props.value).toBe("141001");
  });

  it("dismisses when the backdrop is tapped", () => {
    // The sheet is a full-screen overlay whose only other exit is a button the
    // keyboard can cover -- without this the customer is stuck on a screen that
    // accepts no input and offers no way back.
    const onClose = jest.fn();
    const { getByLabelText } = renderWithProviders(
      <LocationPickerModal visible currentZipcode={null} onClose={onClose} onConfirm={() => {}} />,
    );
    fireEvent.press(getByLabelText("Close change location"));
    return waitFor(() => expect(onClose).toHaveBeenCalledTimes(1));
  });

  it("confirms from the keyboard's done key", async () => {
    // With the sheet lifted above the keyboard the Confirm button is reachable, but
    // the done key is the shorter path once six digits are in.
    const onConfirm = jest.fn();
    const onClose = jest.fn();
    const { getByLabelText } = renderWithProviders(
      <LocationPickerModal visible currentZipcode={null} onClose={onClose} onConfirm={onConfirm} />,
    );
    const field = getByLabelText("ZIP code");
    fireEvent.changeText(field, "141001");
    fireEvent(field, "submitEditing");
    expect(onConfirm).toHaveBeenCalledWith("141001");
    await waitFor(() => expect(onClose).toHaveBeenCalledTimes(1));
  });
});
