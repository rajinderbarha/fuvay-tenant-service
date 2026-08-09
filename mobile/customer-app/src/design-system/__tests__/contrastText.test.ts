import { onColor } from "../contrastText";

describe("onColor", () => {
  it("puts dark text on a light accent", () => {
    // The bug this prevents: white label on #f59e0b amber, unreadable -- and only
    // visible for whichever colour an admin happened to pick.
    expect(onColor("#f59e0b")).toBe("#1A1A1A");
    expect(onColor("#facc15")).toBe("#1A1A1A");
  });

  it("puts white text on a dark accent", () => {
    expect(onColor("#7c3aed")).toBe("#FFFFFF");
    expect(onColor("#1d4ed8")).toBe("#FFFFFF");
    expect(onColor("#000000")).toBe("#FFFFFF");
  });

  it("judges by luminance, not by a channel average", () => {
    // Pure green averages the same as pure blue but is far brighter to the eye;
    // an averaging implementation gets one of these two wrong.
    expect(onColor("#00ff00")).toBe("#1A1A1A");
    expect(onColor("#0000ff")).toBe("#FFFFFF");
  });

  it("agrees with WCAG on the mid-tones, where the choice actually matters", () => {
    // Sky blue #0ea5e9 looks "dark enough for white" but is not: white on it is
    // 2.9:1, near-black 7.2:1. This is the case a midpoint threshold gets wrong.
    expect(onColor("#0ea5e9")).toBe("#1A1A1A");
    expect(onColor("#10b981")).toBe("#1A1A1A");
  });

  it("accepts shorthand and ignores an alpha suffix", () => {
    // Callers append alpha for washes; alpha does not change what is readable on
    // the opaque fill.
    expect(onColor("#fff")).toBe("#1A1A1A");
    expect(onColor("#f59e0b80")).toBe("#1A1A1A");
  });

  it("falls back rather than throwing on a value it cannot read", () => {
    for (const bad of [null, undefined, "", "rgb(1,2,3)", "#12", "#ggghhh"]) {
      expect(onColor(bad)).toBe("#FFFFFF");
    }
    expect(onColor(null, "#123456")).toBe("#123456");
  });
});
