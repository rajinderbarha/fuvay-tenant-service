import "@testing-library/jest-dom/vitest";
import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import { RepairEstimateGuidanceEditor } from "../RepairEstimateGuidanceEditor";

describe("RepairEstimateGuidanceEditor", () => {
  it("reveals the guidance range and reports edited values", () => {
    const onEnabledChange = vi.fn();
    const onMinimumChange = vi.fn();
    const onMaximumChange = vi.fn();
    const { rerender } = render(
      <RepairEstimateGuidanceEditor
        enabled={false}
        minimum=""
        maximum=""
        onEnabledChange={onEnabledChange}
        onMinimumChange={onMinimumChange}
        onMaximumChange={onMaximumChange}
      />,
    );

    fireEvent.click(screen.getByRole("switch", { name: /Show customers a rough range/ }));
    expect(onEnabledChange).toHaveBeenCalledWith(true);

    rerender(
      <RepairEstimateGuidanceEditor
        enabled
        minimum="1200"
        maximum="2500"
        onEnabledChange={onEnabledChange}
        onMinimumChange={onMinimumChange}
        onMaximumChange={onMaximumChange}
      />,
    );
    fireEvent.change(screen.getByLabelText("Minimum rough repair estimate"), { target: { value: "1400" } });
    fireEvent.change(screen.getByLabelText("Maximum rough repair estimate"), { target: { value: "2800" } });

    expect(onMinimumChange).toHaveBeenCalledWith("1400");
    expect(onMaximumChange).toHaveBeenCalledWith("2800");
  });
});
