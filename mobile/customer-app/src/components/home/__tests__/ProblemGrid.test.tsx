import React from "react";
import { screen, fireEvent } from "@testing-library/react-native";
import { renderWithProviders } from "../../../testing/renderWithProviders";
import { ProblemGrid } from "../ProblemGrid";
import { HomeQuickIssue } from "../../../domain/customerHome";
import { asCategoryId } from "../../../domain/ids";

function issue(label: string, category = "Air Conditioning"): HomeQuickIssue {
  return {
    issueId: `i-${label}`,
    label,
    categoryId: asCategoryId("cat-1"),
    categorySlug: "air-conditioning",
    categoryName: category,
    iconUrl: null,
  };
}

const SEVEN = [
  "AC Not Cooling", "AC Not Starting", "Bad Smell", "Water Leaking",
  "Noisy Unit", "Gas Refill Needed", "Remote Not Working",
].map(l => issue(l));

describe("ProblemGrid", () => {
  it("shows the problems as a grid so nothing is hidden off-screen", () => {
    // The horizontal rail this replaces hid most of its contents: whether "AC
    // Not Cooling" was on offer depended on the customer thinking to swipe.
    renderWithProviders(<ProblemGrid issues={SEVEN} onPressIssue={() => {}} />);
    for (const i of SEVEN) expect(screen.getByText(i.label)).toBeTruthy();
  });

  it("carries the chosen problem straight into the booking flow", () => {
    const onPressIssue = jest.fn();
    renderWithProviders(<ProblemGrid issues={SEVEN} onPressIssue={onPressIssue} />);
    fireEvent.press(screen.getByLabelText("Bad Smell, Air Conditioning"));
    expect(onPressIssue).toHaveBeenCalledWith(SEVEN[2]);
  });


  it("shows exactly what it is given, with no See-all and no More tile", () => {
    // Both were removed by request: the caller decides how many (selectProblems)
    // and the circles section further down carries a different selection, so
    // browsing happens in the page rather than behind a sheet.
    const many = [...SEVEN, issue("Thermostat Faulty"), issue("Drain Blocked", "Plumbing")];
    renderWithProviders(<ProblemGrid issues={many} onPressIssue={() => {}} />);
    expect(screen.queryByText(/more$/)).toBeNull();
    expect(screen.queryByText("See all")).toBeNull();
    // Every one it was handed is rendered -- nothing is hidden behind an
    // affordance that no longer exists.
    for (const i of many) expect(screen.getByText(i.label)).toBeTruthy();
  });


  it("drops a problem that cannot open the assistant rather than rendering a dead tile", () => {
    const broken = { ...issue("Unroutable"), categorySlug: null };
    renderWithProviders(<ProblemGrid issues={[...SEVEN, broken]} onPressIssue={() => {}} />);
    expect(screen.queryByText("Unroutable")).toBeNull();
  });

  it("renders nothing at all when there are no problems", () => {
    const { toJSON } = renderWithProviders(<ProblemGrid issues={[]} onPressIssue={() => {}} />);
    // A heading over an empty grid would read as a section that failed to load.
    expect(JSON.stringify(toJSON())).not.toContain("problem");
  });

  it("never shows severity, which is a dispatch grading and not the customer's business", () => {
    renderWithProviders(<ProblemGrid issues={SEVEN} onPressIssue={() => {}} />);
    for (const word of [/critical/i, /high/i, /urgent/i]) {
      expect(screen.queryByText(word)).toBeNull();
    }
  });

  it("uses the admin heading when one is set", () => {
    renderWithProviders(
      <ProblemGrid issues={SEVEN} title="Kya problem hai?" onPressIssue={() => {}} />,
    );
    expect(screen.getByText("Kya problem hai?")).toBeTruthy();
    expect(screen.queryByText("What's the problem?")).toBeNull();
  });
});
