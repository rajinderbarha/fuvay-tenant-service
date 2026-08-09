import React from "react";
import { screen } from "@testing-library/react-native";
import { renderWithProviders } from "../../../testing/renderWithProviders";
import { AssuranceSection, ASSURANCE_POINTS } from "../AssuranceSection";

describe("AssuranceSection", () => {
  it("substantiates every claim instead of listing slogans", () => {
    // The three tiles this replaces said "Verified Expert", "Transparent
    // Pricing", "Status Update" and nothing else -- claims with nothing under
    // them read as decoration, which is the opposite of a trust section's job.
    renderWithProviders(<AssuranceSection />);
    for (const point of ASSURANCE_POINTS) {
      expect(screen.getByText(point.label)).toBeTruthy();
      expect(screen.getByText(point.detail)).toBeTruthy();
    }
  });

  it("only makes claims the platform actually keeps", () => {
    // Each of these maps to something real: tenant verification gates the
    // Verified Business badge; the review screen shows the visit fee and its
    // credit, and parts need explicit customer approval; masked calling bridges
    // the call so neither number is exposed. Nothing here asserts 24/7 support,
    // a guarantee or an insurance claim -- none of which exist.
    renderWithProviders(<AssuranceSection />);
    expect(screen.queryByText(/24\/7/)).toBeNull();
    expect(screen.queryByText(/guarantee/i)).toBeNull();
    expect(screen.queryByText(/insured|insurance/i)).toBeNull();
    expect(screen.queryByText(/money.?back/i)).toBeNull();
  });

  it("uses the admin heading when the section settings set one", () => {
    renderWithProviders(<AssuranceSection title="Our promise to you" />);
    expect(screen.getByText("Our promise to you")).toBeTruthy();
    expect(screen.queryByText("What you're promised")).toBeNull();
  });

  it("renders whatever points it is given rather than a fixed three", () => {
    renderWithProviders(
      <AssuranceSection
        points={[{ key: "k", label: "One point", detail: "Its substantiation.", icon: "shield-checkmark-outline" }]}
      />,
    );
    expect(screen.getByText("One point")).toBeTruthy();
    expect(screen.queryByText("Checked providers")).toBeNull();
  });
});
