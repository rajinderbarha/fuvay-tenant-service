import React from "react";
import { screen, fireEvent } from "@testing-library/react-native";
import { renderWithProviders } from "../../../testing/renderWithProviders";
import { ProblemCircles } from "../ProblemCircles";
import { HomeQuickIssue } from "../../../domain/customerHome";
import { asCategoryId } from "../../../domain/ids";

function issue(n: number, slug: string | null = "air-conditioning"): HomeQuickIssue {
  return {
    issueId: `i-${n}`,
    label: `Problem ${n}`,
    categoryId: asCategoryId("cat-1"),
    categorySlug: slug,
    categoryName: "Air Conditioning",
    iconUrl: null,
    intent: "repair" as const,
  };
}

const TWELVE = Array.from({ length: 12 }, (_, i) => issue(i + 1));

describe("ProblemCircles", () => {
  it("shows every problem it is given", () => {
    renderWithProviders(<ProblemCircles issues={TWELVE} onPressIssue={() => {}} />);
    for (const i of TWELVE) expect(screen.getByText(i.label)).toBeTruthy();
  });

  it("books straight from a circle, with the category carried along", () => {
    const onPressIssue = jest.fn();
    renderWithProviders(<ProblemCircles issues={TWELVE} onPressIssue={onPressIssue} />);
    fireEvent.press(screen.getByLabelText("Problem 5, Air Conditioning"));
    expect(onPressIssue).toHaveBeenCalledWith(TWELVE[4]);
  });

  it("drops a problem that cannot open the assistant", () => {
    renderWithProviders(
      <ProblemCircles issues={[...TWELVE, issue(99, null)]} onPressIssue={() => {}} />,
    );
    expect(screen.queryByText("Problem 99")).toBeNull();
  });

  it("renders nothing when there is nothing to show", () => {
    const { queryByText } = renderWithProviders(
      <ProblemCircles issues={[]} onPressIssue={() => {}} />,
    );
    // No heading over an empty section: that reads as a failure to load.
    expect(queryByText(/More things we fix/)).toBeNull();
  });

  it("uses the admin heading when the layout settings set one", () => {
    renderWithProviders(
      <ProblemCircles issues={TWELVE} title="Aur kya theek karein?" onPressIssue={() => {}} />,
    );
    expect(screen.getByText("Aur kya theek karein?")).toBeTruthy();
    expect(screen.queryByText("More things we fix")).toBeNull();
  });

  it("shows no severity and no price, like the tile grid", () => {
    renderWithProviders(<ProblemCircles issues={TWELVE} onPressIssue={() => {}} />);
    expect(screen.queryByText(/critical|urgent/i)).toBeNull();
    expect(screen.queryByText(/₹/)).toBeNull();
  });
});
