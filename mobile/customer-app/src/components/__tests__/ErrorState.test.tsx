import React from "react";
import { fireEvent } from "@testing-library/react-native";
import { ErrorState } from "../feedback/ErrorState";
import { renderWithTheme } from "../../testing/render-with-theme";

describe("ErrorState", () => {
  it("exposes an alert role for screen readers", () => {
    const { getByRole } = renderWithTheme(<ErrorState title="Couldn't load this" />);
    expect(getByRole("alert")).toBeTruthy();
  });

  it("shows the error reference id when provided", () => {
    const { getByText } = renderWithTheme(<ErrorState title="Couldn't load this" errorReferenceId="err_abc123" />);
    expect(getByText(/err_abc123/)).toBeTruthy();
  });

  it("fires the retry action", () => {
    const onRetry = jest.fn();
    const { getByText } = renderWithTheme(<ErrorState title="Couldn't load this" onRetry={onRetry} />);
    fireEvent.press(getByText("Retry"));
    expect(onRetry).toHaveBeenCalledTimes(1);
  });

  it("renders no server stack trace text", () => {
    const { queryByText } = renderWithTheme(<ErrorState title="Couldn't load this" description="Something went wrong on our end." />);
    expect(queryByText(/Traceback|at Object\.|node_modules/)).toBeNull();
  });
});
