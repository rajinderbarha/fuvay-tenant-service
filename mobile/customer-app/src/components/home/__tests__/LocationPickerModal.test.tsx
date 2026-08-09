import React from "react";
import { Keyboard } from "react-native";
import { fireEvent } from "@testing-library/react-native";
import { renderWithProviders } from "../../../testing/renderWithProviders";
import { LocationPickerModal } from "../LocationPickerModal";

describe("LocationPickerModal", () => {
  it("rejects an incomplete ZIP code without calling onConfirm", () => {
    const onConfirm = jest.fn();
    const { getByLabelText, getByText, findByText } = renderWithProviders(
      <LocationPickerModal visible currentZipcode={null} onClose={() => {}} onConfirm={onConfirm} />,
    );
    fireEvent.changeText(getByLabelText("ZIP code"), "141");
    fireEvent.press(getByText("Confirm location"));
    return findByText(/valid 6-digit ZIP code/).then(() => {
      expect(onConfirm).not.toHaveBeenCalled();
    });
  });

  it("confirms a valid 6-digit ZIP and closes", () => {
    const onConfirm = jest.fn();
    const onClose = jest.fn();
    const { getByLabelText, getByText } = renderWithProviders(
      <LocationPickerModal visible currentZipcode={null} onClose={onClose} onConfirm={onConfirm} />,
    );
    fireEvent.changeText(getByLabelText("ZIP code"), "141001");
    fireEvent.press(getByText("Confirm location"));
    expect(onConfirm).toHaveBeenCalledWith("141001");
    expect(onClose).toHaveBeenCalledTimes(1);
  });

  it("puts the number pad away on confirm, not just the sheet", () => {
    // The field lives inside a Modal, and unmounting a focused TextInput with the
    // keyboard up leaves the keyboard on screen -- a number pad covering half of Home
    // with nothing focused to dismiss it by tapping.
    const dismiss = jest.spyOn(Keyboard, "dismiss");
    const { getByLabelText, getByText } = renderWithProviders(
      <LocationPickerModal visible currentZipcode={null} onClose={() => {}} onConfirm={() => {}} />,
    );
    fireEvent.changeText(getByLabelText("ZIP code"), "141001");
    fireEvent.press(getByText("Confirm location"));
    expect(dismiss).toHaveBeenCalled();
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
    expect(onClose).toHaveBeenCalledTimes(1);
    dismiss.mockRestore();
  });

  it("pre-fills the current ZIP when reopened", () => {
    const { getByLabelText } = renderWithProviders(
      <LocationPickerModal visible currentZipcode="141001" onClose={() => {}} onConfirm={() => {}} />,
    );
    expect(getByLabelText("ZIP code").props.value).toBe("141001");
  });
});
