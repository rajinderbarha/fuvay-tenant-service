import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import React from "react";
import { EmptyState } from "../components/StateViews";

describe("EmptyState", () => {
  it("renders title and description", () => {
    render(<EmptyState title="No bookings yet" description="Bookings will appear here once created." />);
    expect(screen.getByText("No bookings yet")).toBeInTheDocument();
    expect(screen.getByText("Bookings will appear here once created.")).toBeInTheDocument();
  });

  it("renders provided actions", () => {
    render(<EmptyState title="No data" primaryAction={<button>Create booking</button>} />);
    expect(screen.getByRole("button", { name: "Create booking" })).toBeInTheDocument();
  });
});
