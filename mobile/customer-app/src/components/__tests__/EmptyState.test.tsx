import React from "react";
import { fireEvent } from "@testing-library/react-native";
import { EmptyState } from "../feedback/EmptyState";
import { renderWithTheme } from "../../testing/render-with-theme";

describe("EmptyState", () => {
  it("renders title and description", () => {
    const { getByText } = renderWithTheme(<EmptyState title="No bookings yet" description="Book your first service to see it here." />);
    expect(getByText("No bookings yet")).toBeTruthy();
    expect(getByText("Book your first service to see it here.")).toBeTruthy();
  });

  it("fires the primary action", () => {
    const onPress = jest.fn();
    const { getByText } = renderWithTheme(<EmptyState title="No results" primaryAction={{ label: "Reset filters", onPress }} />);
    fireEvent.press(getByText("Reset filters"));
    expect(onPress).toHaveBeenCalledTimes(1);
  });

  it("renders without any action when none is provided", () => {
    const { queryByRole } = renderWithTheme(<EmptyState title="No results" />);
    expect(queryByRole("button")).toBeNull();
  });
});
