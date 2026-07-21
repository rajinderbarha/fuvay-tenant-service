/**
 * NOTE (MODE B / build-blocked): written against the same vitest +
 * @testing-library/react API the design-system package already uses.
 * NOT executed — see docs/design/ux-02-super-admin/frontend-test-report.md.
 */
import { describe, it, expect } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import { RoleDashboard } from "../../components/ux02/widgets/RoleDashboard";
import { EnterpriseDetailPage } from "../../components/ux02/patterns/EnterpriseDetailPage";
import { ReviewApprovalWorkspace } from "../../components/ux02/patterns/ReviewApprovalWorkspace";

describe("RoleDashboard", () => {
  it("shows finance widget for admin_finance and super_admin only", () => {
    const { unmount } = render(<RoleDashboard role="admin_finance" />);
    expect(screen.getByText(/Package Credit \(all tenants\)/)).toBeTruthy();
    unmount();
    render(<RoleDashboard role="admin_operations" />);
    expect(screen.queryByText(/Package Credit \(all tenants\)/)).toBeNull();
  });

  it("shows the security risk overview only for admin_security / super_admin", () => {
    render(<RoleDashboard role="admin_security" />);
    expect(screen.getByText("Risk Overview")).toBeTruthy();
  });
});

describe("EnterpriseDetailPage", () => {
  it("switches sections via the nav buttons (keyboard/click operable)", () => {
    render(
      <EnterpriseDetailPage
        title="Test Tenant"
        readiness="MOCK_DESIGN_ONLY"
        sections={[
          { id: "a", label: "Section A", content: <div>Content A</div> },
          { id: "b", label: "Section B", content: <div>Content B</div> },
        ]}
      />
    );
    expect(screen.getByText("Content A")).toBeTruthy();
    // The component intentionally renders the section label twice: once as
    // a desktop <nav> <button> and once as a mobile <select> <option>,
    // toggled between via a CSS media query (jsdom does not evaluate media
    // queries, so both are present in the accessibility tree during tests).
    // Scope to the button role so the click targets the desktop nav item,
    // not the ambiguous "Section B" text shared with the <option>.
    fireEvent.click(screen.getByRole("button", { name: "Section B" }));
    expect(screen.getByText("Content B")).toBeTruthy();
  });

  it("exposes a mobile section-jump select with matching options", () => {
    render(
      <EnterpriseDetailPage
        title="Test Tenant"
        readiness="MOCK_DESIGN_ONLY"
        sections={[{ id: "a", label: "Section A", content: <div>Content A</div> }]}
      />
    );
    expect(screen.getByLabelText("Jump to section")).toBeTruthy();
  });
});

describe("ReviewApprovalWorkspace", () => {
  it("disables Reject until a reason is entered, and requires confirmation before deciding", () => {
    let decided: string | null = null;
    render(
      <ReviewApprovalWorkspace
        title="Review"
        summary={<div>Applicant summary</div>}
        checklist={[{ id: "c1", label: "ID verified", status: "pass" }]}
        documents={[{ id: "d1", label: "Government ID" }]}
        onDecision={(d) => { decided = d; }}
      />
    );
    const rejectButton = screen.getByText("Reject") as HTMLButtonElement;
    expect(rejectButton.disabled).toBe(true);

    fireEvent.change(screen.getByLabelText("Decision reason"), { target: { value: "Missing document" } });
    expect((screen.getByText("Reject") as HTMLButtonElement).disabled).toBe(false);

    fireEvent.click(screen.getByText("Approve"));
    expect(screen.getByRole("alertdialog")).toBeTruthy();
    expect(decided).toBeNull(); // not yet confirmed

    fireEvent.click(screen.getByText("Confirm"));
    expect(decided).toBe("approve");
  });
});
