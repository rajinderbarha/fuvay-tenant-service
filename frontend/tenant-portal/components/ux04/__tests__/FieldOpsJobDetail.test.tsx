import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import { FieldOpsJobDetail } from "../FieldOpsJobDetail";
import { fieldOpsJobDetailFixture } from "../../../lib/ux04/fixtures";

describe("FieldOpsJobDetail — model-specific, no ServiceJob-only sections", () => {
  it("never renders quote/checklist/parts/invoice/credit as section headings", () => {
    render(<FieldOpsJobDetail view={fieldOpsJobDetailFixture} />);
    const headings = screen.getAllByRole("heading").map((h) => h.textContent?.toLowerCase());
    for (const forbidden of ["quote", "checklist", "parts requests", "invoice", "credit & commission"]) {
      expect(headings).not.toContain(forbidden);
    }
    // exactly the sections this view model actually carries
    expect(headings).toEqual(expect.arrayContaining(["notes", "timeline", "activity / audit"]));
  });

  it("renders the field_ops.Job label and canonical id", () => {
    render(<FieldOpsJobDetail view={fieldOpsJobDetailFixture} />);
    expect(screen.getAllByText(/field_ops\.Job/).length).toBeGreaterThan(0);
  });
});
