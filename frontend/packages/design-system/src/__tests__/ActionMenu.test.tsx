import React from "react";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import { ActionMenu } from "../components/ActionMenu";

describe("ActionMenu", () => {
  it("portals actions outside clipping containers and invokes the selected action", async () => {
    const onEdit = vi.fn();
    const user = userEvent.setup();
    const { container } = render(
      <div data-testid="clipping-container" style={{ overflow: "hidden" }}>
        <ActionMenu items={[{ label: "Edit provider", onClick: onEdit }]} />
      </div>,
    );

    await user.click(screen.getByRole("button", { name: "Actions" }));
    const menu = screen.getByRole("menu");
    expect(document.body.contains(menu)).toBe(true);
    expect(container.contains(menu)).toBe(false);

    await user.click(screen.getByRole("menuitem", { name: "Edit provider" }));
    expect(onEdit).toHaveBeenCalledOnce();
    expect(screen.queryByRole("menu")).not.toBeInTheDocument();
  });

  it("closes with Escape and restores focus to its trigger", async () => {
    const user = userEvent.setup();
    render(<ActionMenu items={[{ label: "Archive", onClick: vi.fn() }]} />);
    const trigger = screen.getByRole("button", { name: "Actions" });
    await user.click(trigger);
    await user.keyboard("{Escape}");
    expect(screen.queryByRole("menu")).not.toBeInTheDocument();
    expect(trigger).toHaveFocus();
  });
});
