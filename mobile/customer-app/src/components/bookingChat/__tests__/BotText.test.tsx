import React from "react";
import { StyleSheet } from "react-native";

import { renderWithProviders } from "../../../testing/renderWithProviders";
import { fuvayFontFamily } from "../../../design-system/tokens/fonts";
import { BotText } from "../BotText";

/**
 * These assert the RULE, not a snapshot: a custom TTF is selected by family
 * name alone, so a chat bubble that declares only `fontWeight` renders in the
 * system font. That is exactly the defect this component exists to close --
 * the assistant flow was the one screen of the four not in Barlow.
 */
function familyOf(node: { props: { style?: unknown } }): string | undefined {
  return (StyleSheet.flatten(node.props.style) as { fontFamily?: string } | undefined)?.fontFamily;
}

describe("BotText", () => {
  it("gives unweighted text the regular Barlow family", () => {
    const { getByText } = renderWithProviders(<BotText>Hello</BotText>);
    expect(familyOf(getByText("Hello"))).toBe(fuvayFontFamily.regular);
  });

  it.each([
    ["500", fuvayFontFamily.medium],
    ["600", fuvayFontFamily.semibold],
    ["700", fuvayFontFamily.bold],
    ["800", fuvayFontFamily.bold],
  ] as const)("maps fontWeight %s to its own registered family", (weight, expected) => {
    const { getByText } = renderWithProviders(
      <BotText style={{ fontWeight: weight }}>Weighted</BotText>,
    );
    expect(familyOf(getByText("Weighted"))).toBe(expected);
  });

  it("keeps fontWeight alongside the family", () => {
    // Not redundant: it is the only weight signal on the first frame and in
    // tests, where the TTFs are never registered and RN falls back to the
    // system font. Dropping it would flatten every heading to regular.
    const { getByText } = renderWithProviders(
      <BotText style={{ fontWeight: "700" }}>Bold</BotText>,
    );
    const flat = StyleSheet.flatten(getByText("Bold").props.style) as { fontWeight?: string };
    expect(flat.fontWeight).toBe("700");
  });

  it("never overrides an explicit family, so mono labels survive", () => {
    const { getByText } = renderWithProviders(
      <BotText style={{ fontFamily: fuvayFontFamily.mono, fontWeight: "700" }}>SLOT</BotText>,
    );
    expect(familyOf(getByText("SLOT"))).toBe(fuvayFontFamily.mono);
  });

  it("preserves the caller's other style properties", () => {
    const { getByText } = renderWithProviders(
      <BotText style={{ fontSize: 14.5, color: "#ff0000" }}>Sized</BotText>,
    );
    const flat = StyleSheet.flatten(getByText("Sized").props.style) as Record<string, unknown>;
    expect(flat.fontSize).toBe(14.5);
    expect(flat.color).toBe("#ff0000");
  });

  it("accepts an array style, as the flow's call sites use", () => {
    const { getByText } = renderWithProviders(
      <BotText style={[{ fontSize: 12 }, { fontWeight: "600" }]}>Composed</BotText>,
    );
    const flat = StyleSheet.flatten(getByText("Composed").props.style) as Record<string, unknown>;
    expect(flat.fontFamily).toBe(fuvayFontFamily.semibold);
    expect(flat.fontSize).toBe(12);
  });
});
