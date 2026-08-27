import React from "react";
import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { TableSurface } from "../components/TableSurface";

describe("TableSurface", () => {
  it("applies the canonical table contract and selected density", () => {
    render(
      <TableSurface density="compact" aria-label="Providers">
        <tbody><tr><td>Acme Services</td></tr></tbody>
      </TableSurface>,
    );

    const table = screen.getByRole("table", { name: "Providers" });
    expect(table).toHaveClass("ds-table");
    expect(table).toHaveAttribute("data-density", "compact");
    expect(screen.getByText("Acme Services")).toBeInTheDocument();
  });
});
