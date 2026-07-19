import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import { StatusTransitionPanel } from "../StatusTransitionPanel";

describe("StatusTransitionPanel — invalid/skipped/repeated-terminal transitions", () => {
  it("flags an out-of-sequence transition rather than hiding it silently", () => {
    render(
      <StatusTransitionPanel
        transition={{
          currentStatus: "assigned",
          allowedNext: [{ toStatus: "completed", requiredFieldsOrEvidence: [], customerVisibleEffect: "job done", financeEffect: null }],
        }}
      />
    );
    expect(screen.getByText(/out-of-sequence transition/i)).toBeInTheDocument();
  });

  it("renders no further transition option for a completed (terminal) job", () => {
    render(<StatusTransitionPanel transition={{ currentStatus: "completed", allowedNext: [] }} />);
    expect(screen.getByText(/terminal state/i)).toBeInTheDocument();
  });

  it("renders an honest blocked message when allowedNext is empty on a non-terminal status", () => {
    render(<StatusTransitionPanel transition={{ currentStatus: "in_progress", allowedNext: [] }} />);
    expect(screen.getByText(/no allowed transition/i)).toBeInTheDocument();
  });
});
