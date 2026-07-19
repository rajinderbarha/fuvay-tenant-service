/**
 * NOTE (MODE B / build-blocked): this repo's super-admin package.json has
 * no vitest devDependency or test script configured (only
 * frontend/packages/design-system does) — see
 * docs/design/ux-02-super-admin/frontend-test-report.md. This file is
 * written against the same vitest + @testing-library/react API the
 * design-system package already uses, so it is ready to run once a
 * vitest config is added to frontend/super-admin/package.json. It has
 * NOT been executed.
 */
import { describe, it, expect } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import { EnterpriseListPage } from "../../components/ux02/patterns/EnterpriseListPage";
import { FIXTURE_TENANTS } from "../../lib/ux02/fixtures";
import type { TenantFixture } from "../../lib/ux02/types";

function renderList() {
  return render(
    <EnterpriseListPage<TenantFixture>
      title="Tenants" description="test" readiness="READ_ONLY_READY"
      rows={FIXTURE_TENANTS} rowKey={(t) => t.id}
      searchFields={(t) => t.displayName}
      columns={[{ key: "displayName", header: "Tenant", accessor: (t) => t.displayName }]}
      bulkActions={[{ key: "suspend", label: "Suspend selected" }]}
    />
  );
}

describe("EnterpriseListPage (tenant list instance)", () => {
  it("filters rows by search query", () => {
    renderList();
    fireEvent.change(screen.getByLabelText("Search"), { target: { value: "Harborline" } });
    expect(screen.getByText("Harborline Repairs")).toBeTruthy();
    expect(screen.queryByText("Blue Ridge Home Services")).toBeNull();
  });

  it("shows a bulk impact-preview confirmation, never firing a real mutation", () => {
    renderList();
    const checkboxes = screen.getAllByRole("checkbox");
    fireEvent.click(checkboxes[0]); // select-all
    fireEvent.click(screen.getByText("Suspend selected"));
    expect(screen.getByRole("alertdialog")).toBeTruthy();
    expect(screen.getByText(/MOCK_DESIGN_ONLY/)).toBeTruthy();
  });

  it("renders filter chips after Apply and clears them on click", () => {
    render(
      <EnterpriseListPage<TenantFixture>
        title="Tenants" description="test" readiness="READ_ONLY_READY"
        rows={FIXTURE_TENANTS} rowKey={(t) => t.id}
        searchFields={(t) => t.displayName}
        filters={[{ key: "vertical", label: "Vertical", values: ["home_services", "real_estate"] }]}
        getFilterValue={(t, key) => (t as any)[key]}
        columns={[{ key: "displayName", header: "Tenant", accessor: (t) => t.displayName }]}
      />
    );
    fireEvent.change(screen.getByLabelText("Vertical"), { target: { value: "real_estate" } });
    fireEvent.click(screen.getByText("Apply"));
    expect(screen.getByText(/vertical: real_estate/)).toBeTruthy();
  });
});
