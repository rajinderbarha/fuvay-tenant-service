import React from "react";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import { EnterpriseFilterBar } from "../components/EnterpriseFilterBar";

describe("EnterpriseFilterBar", () => {
  it("uses one filter contract for quick filters and portal applications", async () => {
    const onChange = vi.fn();
    const onSearch = vi.fn();
    const user = userEvent.setup();
    render(
      <EnterpriseFilterBar
        filters={[{ key: "status", label: "Status", type: "select", options: [{ value: "active", label: "Active" }] }]}
        values={{ status: "" }}
        onChange={onChange}
        onReset={vi.fn()}
        onSearch={onSearch}
      />,
    );

    await user.selectOptions(screen.getByRole("combobox"), "active");
    expect(onChange).toHaveBeenCalledWith("status", "active");
  });
});
