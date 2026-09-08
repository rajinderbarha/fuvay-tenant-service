import "@testing-library/jest-dom/vitest";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { useState } from "react";
import { describe, expect, it, vi } from "vitest";
import { BrandCoverageSelector } from "../BrandCoverageSelector";

const candidates = [
  { brand_id: "daikin", name: "Daikin", is_enabled: true },
  { brand_id: "lg", name: "LG", is_enabled: false },
];

describe("BrandCoverageSelector", () => {
  it("saves all brands together, then supports selecting a subset and reloading it", async () => {
    const save = vi.fn().mockResolvedValue(undefined);
    function Editor() {
      const [brands, setBrands] = useState(candidates);
      return <BrandCoverageSelector brands={brands} onChange={async ids => {
        await save(ids);
        setBrands(current => current.map(brand => ({ ...brand, is_enabled: ids.includes(brand.brand_id) })));
      }}/>;
    }
    const view = render(<Editor/>);
    fireEvent.click(screen.getByRole("button", { name: "All brands" }));
    await waitFor(() => expect(screen.getByRole("button", { name: "All brands" })).toHaveAttribute("aria-pressed", "true"));
    expect(save).toHaveBeenCalledExactlyOnceWith(["daikin", "lg"]);
    expect(screen.queryByRole("button", { name: "LG" })).not.toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Specific brands" }));
    expect(save).toHaveBeenCalledTimes(1);
    fireEvent.click(screen.getByRole("button", { name: "LG" }));
    await waitFor(() => expect(screen.getByRole("button", { name: "LG" })).toHaveAttribute("aria-pressed", "false"));
    expect(save).toHaveBeenLastCalledWith(["daikin"]);
    view.unmount();
    render(<BrandCoverageSelector brands={candidates} onChange={save}/>);
    expect(screen.getByRole("button", { name: "Specific brands" })).toHaveAttribute("aria-pressed", "true");
    expect(screen.getByRole("button", { name: "Daikin" })).toHaveAttribute("aria-pressed", "true");
    expect(screen.getByRole("button", { name: "LG" })).toHaveAttribute("aria-pressed", "false");
  });

  it("retains the saved subset when selecting All brands fails", async () => {
    render(<BrandCoverageSelector brands={candidates} onChange={vi.fn().mockRejectedValue(new Error("Network unavailable"))}/>);
    fireEvent.click(screen.getByRole("button", { name: "All brands" }));
    expect(await screen.findByRole("alert")).toHaveTextContent("Network unavailable");
    expect(screen.getByRole("button", { name: "Specific brands" })).toHaveAttribute("aria-pressed", "true");
    expect(screen.getByRole("button", { name: "LG" })).toHaveAttribute("aria-pressed", "false");
  });
});
