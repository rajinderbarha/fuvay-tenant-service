import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import { SLAIndicator } from "../SLAIndicator";
import { OperationalActionQueue } from "../OperationalActionQueue";
import { slaGalleryFixture } from "../../../lib/ux04/fixtures";

describe("SLAIndicator — all 9 states render a distinct label", () => {
  it("renders the correct label for every SLAState value", () => {
    for (const sla of slaGalleryFixture) {
      const { unmount } = render(<SLAIndicator sla={sla} />);
      expect(screen.getByText(sla.label)).toBeInTheDocument();
      unmount();
    }
  });
});

describe("OperationalActionQueue — empty and restricted states", () => {
  it("renders an honest empty-state message, not a blank list, when there are no items", () => {
    render(<OperationalActionQueue items={[]} />);
    expect(screen.getByText(/no items need action/i)).toBeInTheDocument();
  });
});
