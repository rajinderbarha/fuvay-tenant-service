import React from "react";
import { fireEvent } from "@testing-library/react-native";
import { renderWithProviders } from "../../../testing/renderWithProviders";
import { OtpCellInput } from "../OtpCellInput";

describe("OtpCellInput", () => {
  it("is exposed as a single logical accessible input", () => {
    const { getAllByLabelText } = renderWithProviders(<OtpCellInput value="" onChange={() => {}} />);
    expect(getAllByLabelText("Verification code")).toHaveLength(1);
  });

  it("sanitizes non-numeric characters and caps at the configured length", () => {
    const onChange = jest.fn();
    const { getByLabelText } = renderWithProviders(<OtpCellInput value="" onChange={onChange} />);
    fireEvent.changeText(getByLabelText("Verification code"), "Your code is: 284176 - thanks");
    expect(onChange).toHaveBeenCalledWith("284176");
  });

  it("calls onSubmitComplete only once the full length is reached", () => {
    const onSubmitComplete = jest.fn();
    const { getByLabelText, rerender } = renderWithProviders(
      <OtpCellInput value="12345" onChange={() => {}} onSubmitComplete={onSubmitComplete} />,
    );
    fireEvent.changeText(getByLabelText("Verification code"), "123456");
    expect(onSubmitComplete).toHaveBeenCalledWith("123456");
  });

  it("shows an accessible error message when provided", () => {
    const { getByText } = renderWithProviders(<OtpCellInput value="123456" onChange={() => {}} errorText="Incorrect code" />);
    expect(getByText("Incorrect code")).toBeTruthy();
  });
});
