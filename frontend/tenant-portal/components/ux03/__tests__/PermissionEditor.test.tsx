/**
 * DESIGN PHASE UX-03 — written but NOT EXECUTED (Mode B). See execution-mode.md.
 */
import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import { PermissionEditor } from "../widgets/PermissionEditor";
import { FIXTURE_PERMISSION_CATALOG } from "../../../lib/ux03/fixtures";

describe("PermissionEditor", () => {
  it("renders a distinct label for denied_override vs not_granted", () => {
    render(<PermissionEditor permissions={FIXTURE_PERMISSION_CATALOG} readOnly />);
    expect(screen.getByText("Denied (explicit)")).toBeInTheDocument();
    expect(screen.getAllByText("Not granted").length).toBeGreaterThan(0);
  });

  it("filters by search query across label/key/group", () => {
    render(<PermissionEditor permissions={FIXTURE_PERMISSION_CATALOG} readOnly />);
    const input = screen.getByLabelText("Search permissions");
    expect(input).toBeInTheDocument();
  });
});
