import "@testing-library/jest-dom/vitest";
import { act, fireEvent, render, screen } from "@testing-library/react";
import { createRef } from "react";
import { describe, expect, it, vi } from "vitest";

import {
  InlineDimensionPricingEditor, type InlineDimensionPricingEditorHandle,
} from "../InlineDimensionPricingEditor";

describe("InlineDimensionPricingEditor", () => {
  it("keeps type selection local until the user saves", async () => {
    const editorRef = createRef<InlineDimensionPricingEditorHandle>();
    const onSaveTypes = vi.fn().mockResolvedValue(undefined);
    const onSaveBrands = vi.fn().mockResolvedValue(undefined);
    const onSaveBrand = vi.fn().mockResolvedValue(undefined);
    render(
      <InlineDimensionPricingEditor
        ref={editorRef}
        basePrice={1499}
        types={[
          { id: "split", name: "Split AC", price: 1499, enabled: true },
          { id: "window", name: "Window AC", price: null, enabled: false },
        ]}
        brands={[{ id: "daikin", name: "Daikin", enabled: true }]}
        exceptions={[]}
        onSaveTypes={onSaveTypes}
        onSaveBrands={onSaveBrands}
        onSaveType={vi.fn().mockResolvedValue(undefined)}
        onClearType={vi.fn().mockResolvedValue(undefined)}
        onClearTypePrices={vi.fn().mockResolvedValue(undefined)}
        onSaveBrand={onSaveBrand}
        onClearBrand={vi.fn().mockResolvedValue(undefined)}
      />,
    );

    expect(screen.getByRole("button", { name: "Split AC" })).toHaveAttribute("aria-pressed", "true");
    expect(screen.getByRole("button", { name: "Window AC" })).toHaveAttribute("aria-pressed", "false");
    expect(screen.getByLabelText("Split AC price")).toBeInTheDocument();
    expect(screen.queryByLabelText("Window AC price")).not.toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: "Window AC" }));
    expect(screen.getByLabelText("Window AC price")).toBeInTheDocument();
    expect(onSaveTypes).not.toHaveBeenCalled();

    fireEvent.click(screen.getAllByRole("button", { name: "Specific brands" })[0]);
    fireEvent.click(screen.getByRole("button", { name: "Daikin" }));
    fireEvent.change(screen.getByLabelText("Split AC Daikin price"), { target: { value: "2100" } });
    expect(onSaveBrands).not.toHaveBeenCalled();
    expect(onSaveBrand).not.toHaveBeenCalled();

    await act(async () => { await editorRef.current?.save(); });
    expect(onSaveTypes).toHaveBeenCalledWith(["split", "window"]);
    expect(onSaveBrands).toHaveBeenCalledWith(["daikin"]);
    expect(onSaveBrand).toHaveBeenCalledWith("split", "daikin", 2100);
  });
});
