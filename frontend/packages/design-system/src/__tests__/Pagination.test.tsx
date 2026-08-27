import React from "react";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import { Pagination } from "../components/PortalKit";

describe("Pagination", () => {
  it("reports the visible range and navigates with the canonical controls", async () => {
    const onPage = vi.fn();
    const user = userEvent.setup();

    render(
      <Pagination
        page={2}
        pageSize={25}
        total={95}
        pageCount={4}
        onPage={onPage}
      />,
    );

    expect(screen.getByRole("navigation", { name: "Pagination" })).toBeInTheDocument();
    expect(screen.getByText("26–50 of 95 results")).toBeInTheDocument();
    expect(screen.getByText("Page 2 of 4")).toBeInTheDocument();

    await user.click(screen.getByRole("button", { name: "First page" }));
    await user.click(screen.getByRole("button", { name: "Previous page" }));
    await user.click(screen.getByRole("button", { name: "Next page" }));
    await user.click(screen.getByRole("button", { name: "Last page" }));

    expect(onPage.mock.calls).toEqual([[1], [1], [3], [4]]);
  });

  it("changes page size through the shared row selector", async () => {
    const onPageSize = vi.fn();
    const user = userEvent.setup();

    render(
      <Pagination
        page={1}
        pageSize={25}
        total={100}
        onPage={vi.fn()}
        pageSizes={[25, 50, 100]}
        onPageSize={onPageSize}
      />,
    );

    await user.selectOptions(screen.getByRole("combobox", { name: "Rows per page" }), "50");
    expect(onPageSize).toHaveBeenCalledWith(50);
  });

  it("hides single-page lists unless a caller explicitly keeps the footer visible", () => {
    const { rerender } = render(
      <Pagination page={1} pageSize={25} total={10} onPage={vi.fn()} />,
    );

    expect(screen.queryByRole("navigation", { name: "Pagination" })).not.toBeInTheDocument();

    rerender(
      <Pagination page={1} pageSize={25} total={10} onPage={vi.fn()} alwaysShow />,
    );
    expect(screen.getByRole("navigation", { name: "Pagination" })).toBeInTheDocument();
  });

  it("supports cursor-backed lists without exposing invalid first or last controls", () => {
    render(
      <Pagination
        page={3}
        onPage={vi.fn()}
        hasPrevious
        hasNext={false}
        navigationMode="adjacent"
        alwaysShow
      />,
    );

    expect(screen.getByText("Page 3")).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "First page" })).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Last page" })).not.toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Previous page" })).toBeEnabled();
    expect(screen.getByRole("button", { name: "Next page" })).toBeDisabled();
  });
});
