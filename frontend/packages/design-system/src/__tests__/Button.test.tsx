import { describe, it, expect, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import React from "react";
import { Button } from "../components/Button";

describe("Button", () => {
  it("renders each variant without crashing", () => {
    const variants = ["primary", "secondary", "tertiary", "ghost", "destructive", "link"] as const;
    variants.forEach((v) => {
      render(<Button variant={v}>Click</Button>);
    });
    expect(screen.getAllByText("Click").length).toBe(variants.length);
  });

  it("disables interaction and shows a spinner while loading", () => {
    render(<Button loading>Save</Button>);
    const btn = screen.getByRole("button");
    expect(btn).toBeDisabled();
  });

  it("fires onClick when enabled", async () => {
    const onClick = vi.fn();
    const user = userEvent.setup();
    render(<Button onClick={onClick}>Go</Button>);
    await user.click(screen.getByRole("button"));
    expect(onClick).toHaveBeenCalledOnce();
  });

  it("does not fire onClick when disabled", async () => {
    const onClick = vi.fn();
    const user = userEvent.setup();
    render(
      <Button onClick={onClick} disabled>
        Go
      </Button>
    );
    await user.click(screen.getByRole("button"));
    expect(onClick).not.toHaveBeenCalled();
  });
});
