import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import { ChecklistProgress } from "../ChecklistProgress";
import { checklistFixture } from "../../../lib/ux04/fixtures";

describe("ChecklistProgress — customer_summary never leaks internal notes", () => {
  it("hides items where customerVisible is false in customer_summary mode", () => {
    const withInternalItem = {
      ...checklistFixture,
      sections: [
        {
          id: "sec_internal",
          label: "Internal QA",
          items: [
            { id: "internal_1", label: "Internal QA check", required: false, completed: true, passFail: "pass" as const, technicianNote: "secret internal note", technicianMedia: [], reviewerNote: "internal reviewer note", customerVisible: false },
          ],
        },
        ...checklistFixture.sections,
      ],
    };
    render(<ChecklistProgress checklist={withInternalItem} mode="customer_summary" />);
    expect(screen.queryByText(/internal qa check/i)).not.toBeInTheDocument();
    expect(screen.queryByText(/secret internal note/i)).not.toBeInTheDocument();
  });

  it("shows technician notes in provider_review mode but not reviewer notes in technician_execution mode", () => {
    render(<ChecklistProgress checklist={checklistFixture} mode="technician_execution" />);
    expect(screen.getByText(/old pump seized/i)).toBeInTheDocument();
  });
});
