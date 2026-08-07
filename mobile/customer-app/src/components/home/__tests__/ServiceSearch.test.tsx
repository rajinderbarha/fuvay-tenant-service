import React from "react";
import { fireEvent } from "@testing-library/react-native";
import { renderWithProviders } from "../../../testing/renderWithProviders";
import { ServiceSearch } from "../ServiceSearch";

const SUGGESTIONS = ["Air Conditioning", "Plumbing", "Electrical"];

/**
 * The rotating hint is deliberately hidden from assistive tech
 * (accessibilityElementsHidden), so RNTL's default queries skip it. Every
 * assertion here must opt in explicitly -- without this a "not rendered"
 * assertion passes even when the text IS on screen, which silently makes
 * the negative tests meaningless.
 */
const HIDDEN = { includeHiddenElements: true } as const;

/**
 * These cover WHICH hint is shown and WHEN rotation is suppressed -- the
 * decisions that can actually be wrong. The passage of time itself is not
 * asserted: driving the rotation with fake timers destabilised unrelated
 * suites (the interval re-arms a fade which re-arms the interval, so the
 * timer queue never drains and RNTL's unmount cleanup hangs, taking other
 * files down with it under parallel workers). A test that breaks other
 * tests is worth less than the coverage it adds.
 */
describe("ServiceSearch rotating placeholder", () => {
  it("shows a real bookable service as the hint", () => {
    const { getByText } = renderWithProviders(
      <ServiceSearch value="" onChangeText={() => {}} suggestions={SUGGESTIONS} />,
    );
    expect(getByText("Search Air Conditioning…", HIDDEN)).toBeTruthy();
  });

  it("suppresses the hint once the field has text", () => {
    // A hint moving under the caret while someone types is a distraction.
    const { queryByText } = renderWithProviders(
      <ServiceSearch value="ac" onChangeText={() => {}} suggestions={SUGGESTIONS} />,
    );
    expect(queryByText(/^Search Air Conditioning/, HIDDEN)).toBeNull();
  });

  it("suppresses the hint while the field is focused", () => {
    const { getByLabelText, queryByText } = renderWithProviders(
      <ServiceSearch value="" onChangeText={() => {}} suggestions={SUGGESTIONS} />,
    );
    fireEvent(getByLabelText("Search services"), "focus");
    expect(queryByText(/^Search Air Conditioning/, HIDDEN)).toBeNull();
  });

  it("falls back to the static placeholder when there is nothing bookable", () => {
    // Never invent a suggestion: an empty list means the customer's ZIP has
    // no bookable categories, so there is nothing honest to advertise.
    const { queryByText, getByLabelText } = renderWithProviders(
      <ServiceSearch value="" onChangeText={() => {}} suggestions={[]} />,
    );
    expect(queryByText(/^Search Air Conditioning/, HIDDEN)).toBeNull();
    expect(getByLabelText("Search services").props.placeholder)
      .toBe("Search AC repair, plumbing, cleaning…");
  });

  it("keeps the screen-reader label stable rather than the rotating word", () => {
    // The visible hint changes over time; the accessible name must not, or
    // it gets re-announced on every rotation.
    const { getByLabelText } = renderWithProviders(
      <ServiceSearch value="" onChangeText={() => {}} suggestions={SUGGESTIONS} />,
    );
    expect(getByLabelText("Search services").props.accessibilityHint)
      .toBe("Search AC repair, plumbing, cleaning…");
  });
});
