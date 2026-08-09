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
    const { getByText, getAllByText } = renderWithProviders(
      <ServiceSearch value="" onChangeText={() => {}} suggestions={SUGGESTIONS} />,
    );
    // Two nodes, deliberately: "Search" is fixed and only the service name scrolls,
    // so the box still reads as a search box at every frame of the animation.
    expect(getByText("Search", HIDDEN)).toBeTruthy();
    expect(getAllByText("Air Conditioning…", HIDDEN).length).toBeGreaterThan(0);
  });

  it("repeats the first service at the end of the strip so the loop has no seam", () => {
    // The scroll runs to a pixel-identical copy of the first word and snaps back
    // there, which is what makes the wrap invisible. Without the copy the strip
    // has to jump from the last word to the first, and that jump is visible.
    const { getAllByText } = renderWithProviders(
      <ServiceSearch value="" onChangeText={() => {}} suggestions={SUGGESTIONS} />,
    );
    expect(getAllByText("Air Conditioning…", HIDDEN)).toHaveLength(2);
    expect(getAllByText("Electrical…", HIDDEN)).toHaveLength(1);
  });

  it("stages the NEXT service below the current one, ready to scroll up into place", () => {
    // The whole effect: the words move vertically like a list rather than
    // cross-fading, which needs both rendered inside the clipped one-line strip.
    const { getByText } = renderWithProviders(
      <ServiceSearch value="" onChangeText={() => {}} suggestions={SUGGESTIONS} />,
    );
    expect(getByText("Plumbing…", HIDDEN)).toBeTruthy();
  });

  it("suppresses the hint once the field has text", () => {
    // A hint moving under the caret while someone types is a distraction.
    const { queryByText } = renderWithProviders(
      <ServiceSearch value="ac" onChangeText={() => {}} suggestions={SUGGESTIONS} />,
    );
    expect(queryByText("Air Conditioning…", HIDDEN)).toBeNull();
  });

  it("suppresses the hint while the field is focused", () => {
    const { getByLabelText, queryByText } = renderWithProviders(
      <ServiceSearch value="" onChangeText={() => {}} suggestions={SUGGESTIONS} />,
    );
    fireEvent(getByLabelText("Search services"), "focus");
    expect(queryByText("Air Conditioning…", HIDDEN)).toBeNull();
  });

  it("falls back to the static placeholder when there is nothing bookable", () => {
    // Never invent a suggestion: an empty list means the customer's ZIP has
    // no bookable categories, so there is nothing honest to advertise.
    const { queryByText, getByLabelText } = renderWithProviders(
      <ServiceSearch value="" onChangeText={() => {}} suggestions={[]} />,
    );
    expect(queryByText("Air Conditioning…", HIDDEN)).toBeNull();
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
