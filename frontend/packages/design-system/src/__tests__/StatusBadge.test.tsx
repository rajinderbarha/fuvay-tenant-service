import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import React from "react";
import { StatusBadge } from "../components/StatusBadge";

describe("StatusBadge", () => {
  it("renders a known status with its registered label", () => {
    render(<StatusBadge status="active" />);
    expect(screen.getByText("Active")).toBeInTheDocument();
  });

  it("falls back safely to a neutral badge for an unknown status", () => {
    render(<StatusBadge status="some_weird_future_status" />);
    expect(screen.getByText("Some Weird Future Status")).toBeInTheDocument();
  });

  it("does not throw on an empty status string", () => {
    render(<StatusBadge status="" />);
    expect(screen.getByText("Unknown")).toBeInTheDocument();
  });
});
