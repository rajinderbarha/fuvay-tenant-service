import "@testing-library/jest-dom/vitest";
import { act, fireEvent, render, screen } from "@testing-library/react";
import { createRef } from "react";
import { describe, expect, it, vi } from "vitest";

import {
  InlineDimensionPricingEditor, type InlineDimensionPricingEditorHandle,
} from "../InlineDimensionPricingEditor";

describe("InlineDimensionPricingEditor", () => {
  function setup(brands = [{ id: "daikin", name: "Daikin", enabled: false }]) {
    const ref = createRef<InlineDimensionPricingEditorHandle>();
    const handlers = {
      onSaveTypes: vi.fn().mockResolvedValue(undefined), onSaveBrands: vi.fn().mockResolvedValue(undefined),
      onSaveType: vi.fn().mockResolvedValue(undefined), onClearType: vi.fn().mockResolvedValue(undefined),
      onClearTypePrices: vi.fn().mockResolvedValue(undefined), onSaveBrand: vi.fn().mockResolvedValue(undefined),
      onClearBrand: vi.fn().mockResolvedValue(undefined),
    };
    const props = { basePrice: 1200, types: [{ id: "split", name: "Split AC", price: 1200, enabled: true }], brands, exceptions: [] };
    const view = render(<InlineDimensionPricingEditor ref={ref} {...props} {...handlers} />);
    return { ref, handlers, props, ...view };
  }

  it("persists the visible default All brands on save without requiring a toggle", async () => {
    const { ref, handlers } = setup();
    expect(screen.getByRole("button", { name: "All brands" })).toHaveAttribute("aria-pressed", "true");
    await act(async () => { await ref.current?.save(); });
    expect(handlers.onSaveBrands).toHaveBeenCalledWith(["daikin"]);
    expect(handlers.onClearTypePrices).not.toHaveBeenCalled();
    expect(handlers.onClearBrand).not.toHaveBeenCalled();
  });

  it("names the type with an empty Specific brands selection before writing", async () => {
    const { ref, handlers } = setup();
    fireEvent.click(screen.getByRole("button", { name: "Specific brands" }));
    await act(async () => { await expect(ref.current!.save()).rejects.toThrow("Select at least one supported brand for Split AC, or choose All brands."); });
    expect(handlers.onSaveTypes).not.toHaveBeenCalled();
    expect(handlers.onSaveBrands).not.toHaveBeenCalled();
  });

  it("preserves a saved supported subset instead of silently selecting every brand", async () => {
    const { ref, handlers } = setup([{ id: "daikin", name: "Daikin", enabled: true }, { id: "lg", name: "LG", enabled: false }]);
    expect(screen.getByRole("button", { name: "Specific brands" })).toHaveAttribute("aria-pressed", "true");
    expect(screen.getByRole("button", { name: "Daikin" })).toHaveAttribute("aria-pressed", "true");
    await act(async () => { await ref.current?.save(); });
    expect(handlers.onSaveBrands).toHaveBeenCalledWith(["daikin"]);
    expect(handlers.onSaveTypes).toHaveBeenCalledWith(["split"], { split: { mode: "selected", brand_ids: ["daikin"] } });
  });

  it("does not reset local choices when an intermediate save refreshes server props", () => {
    const { ref, handlers, props, rerender } = setup();
    fireEvent.click(screen.getByRole("button", { name: "Specific brands" }));
    fireEvent.click(screen.getByRole("button", { name: "Daikin" }));
    fireEvent.change(screen.getByLabelText("Split AC Daikin price"), { target: { value: "2100" } });
    rerender(<InlineDimensionPricingEditor ref={ref} {...props} {...handlers} brands={[{ id: "daikin", name: "Daikin", enabled: true }]} />);
    expect(screen.getByRole("button", { name: "Specific brands" })).toHaveAttribute("aria-pressed", "true");
    expect(screen.getByLabelText("Split AC Daikin price")).toHaveValue(2100);
  });

  it("reloads coverage independently of price exceptions, even with one shared price", async () => {
    const { ref, handlers, props, rerender } = setup([
      { id: "daikin", name: "Daikin", enabled: true }, { id: "lg", name: "LG", enabled: true },
    ]);
    rerender(<InlineDimensionPricingEditor ref={ref} {...props} {...handlers}
      types={[
        { id: "split", name: "Split AC", price: null, enabled: true, brandCoverage: { mode: "selected", brand_ids: ["daikin"] } },
        { id: "window", name: "Window AC", price: null, enabled: true, brandCoverage: { mode: "all", brand_ids: [] } },
      ]}
      exceptions={[]}
    />);
    expect(screen.queryByRole("button", { name: "Specific brands" })).not.toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: /Supported types & brands/ }));
    expect(screen.getAllByRole("button", { name: "Specific brands" })[0]).toHaveAttribute("aria-pressed", "true");
    expect(screen.getAllByRole("button", { name: "All brands" })[1]).toHaveAttribute("aria-pressed", "true");
    expect(screen.getByRole("button", { name: "Daikin" })).toHaveAttribute("aria-pressed", "true");
    expect(screen.getByRole("button", { name: "LG" })).toHaveAttribute("aria-pressed", "false");
    expect(screen.getByRole("switch")).toHaveAttribute("aria-checked", "false");
    await act(async () => { await ref.current?.save(); });
    expect(handlers.onSaveTypes).not.toHaveBeenCalled();
    expect(handlers.onClearBrand).not.toHaveBeenCalled();
  });

  it("hides type and brand controls when pricing is switched off and clears only price overrides on save", async () => {
    const { ref, handlers, props, rerender } = setup();
    rerender(<InlineDimensionPricingEditor ref={ref} {...props} {...handlers}
      types={[{ ...props.types[0], brandCoverage: { mode: "selected", brand_ids: ["daikin"] } }]}
      brands={[{ id: "daikin", name: "Daikin", enabled: true }]}
      exceptions={[{ key: "split:daikin", typeId: "split", brandId: "daikin", price: 1500, persisted: true }]}/>);
    fireEvent.click(screen.getByRole("switch", { name: "Price differs by type" }));
    expect(screen.queryByRole("button", { name: "Split AC" })).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Specific brands" })).not.toBeInTheDocument();
    expect(screen.queryByLabelText("Split AC price")).not.toBeInTheDocument();
    expect(handlers.onClearTypePrices).not.toHaveBeenCalled();
    await act(async () => { await ref.current!.save(); });
    expect(handlers.onSaveTypes).toHaveBeenCalledWith(["split"], { split: { mode: "selected", brand_ids: ["daikin"] } });
    expect(handlers.onSaveBrands).toHaveBeenCalledWith(["daikin"]);
    expect(handlers.onClearTypePrices).toHaveBeenCalledOnce();
    expect(handlers.onClearBrand).toHaveBeenCalledWith("split", "daikin");
  });

  it("shows the pricing switch as on for a saved brand override without a type price", () => {
    const { ref, handlers, props, rerender } = setup();
    rerender(<InlineDimensionPricingEditor ref={ref} {...props} {...handlers}
      types={[{ ...props.types[0], price: null }]}
      exceptions={[{ key: "split:daikin", typeId: "split", brandId: "daikin", price: 1500, persisted: true }]}/>);
    expect(screen.getByRole("switch")).toHaveAttribute("aria-checked", "true");
    expect(screen.getByLabelText("Split AC price")).toBeInTheDocument();
  });

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
    expect(onSaveTypes).toHaveBeenCalledWith(["split", "window"], {
      split: { mode: "selected", brand_ids: ["daikin"] },
      window: { mode: "all", brand_ids: [] },
    });
    expect(onSaveBrands).toHaveBeenCalledWith(["daikin"]);
    expect(onSaveBrand).toHaveBeenCalledWith("split", "daikin", 2100);
  });
});
