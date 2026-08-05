import React from "react";
import { render } from "@testing-library/react-native";
import { Text } from "react-native";
import { ErrorBoundary } from "../ErrorBoundary";

function Bomb(): React.ReactElement {
  throw new Error("boom");
}

describe("ErrorBoundary", () => {
  it("renders children when there is no error", () => {
    const { getByText } = render(
      <ErrorBoundary>
        <Text>All good</Text>
      </ErrorBoundary>,
    );
    expect(getByText("All good")).toBeTruthy();
  });

  it("renders a fallback instead of crashing when a child throws", () => {
    const spy = jest.spyOn(console, "error").mockImplementation(() => {});
    const { getByText } = render(
      <ErrorBoundary>
        <Bomb />
      </ErrorBoundary>,
    );
    expect(getByText("Something went wrong")).toBeTruthy();
    spy.mockRestore();
  });
});
