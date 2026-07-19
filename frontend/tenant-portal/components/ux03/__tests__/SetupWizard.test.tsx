/**
 * DESIGN PHASE UX-03 — written but NOT EXECUTED (Mode B). See execution-mode.md.
 */
import { describe, it, expect } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import { SetupWizard, type WizardStep } from "../patterns/SetupWizard";

const steps: WizardStep[] = [
  { id: "a", label: "Step A", render: ({ goNext }) => <button onClick={goNext}>next-a</button> },
  { id: "b", label: "Step B", blocked: true, render: () => <div>step-b</div> },
  { id: "c", label: "Step C", render: () => <div>step-c</div> },
];

describe("SetupWizard", () => {
  it("shows progress and advances on goNext, calling onSaveDraft", () => {
    let saved: string[] = [];
    render(<SetupWizard title="Setup" steps={steps} onSaveDraft={(id) => saved.push(id)} />);
    expect(screen.getByText(/Step 1 of 3/)).toBeInTheDocument();
    fireEvent.click(screen.getByText("next-a"));
    expect(saved).toEqual(["a"]);
  });

  it("blocked steps are disabled in the step nav", () => {
    render(<SetupWizard title="Setup" steps={steps} />);
    const blockedButton = screen.getByText("Step B (optional)".replace(" (optional)", ""), { exact: false });
    expect(blockedButton.closest("button")).toBeDisabled();
  });
});
