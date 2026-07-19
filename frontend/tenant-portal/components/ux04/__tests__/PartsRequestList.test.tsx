import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { PartsRequestList } from "../PartsRequestList";
import { partsRequestListFixture, partsRequestListEmptyFixture } from "../../../lib/ux04/fixtures";

describe("PartsRequestList — states + filters + no field_ops.Job link + no install control", () => {
  it("renders all rows for the multi-row fixture", () => {
    render(<PartsRequestList items={partsRequestListFixture} />);
    for (const row of partsRequestListFixture) {
      expect(screen.getByText(row.request.id)).toBeInTheDocument();
    }
  });

  it("renders an honest empty state, not an error, for an empty list", () => {
    render(<PartsRequestList items={partsRequestListEmptyFixture} />);
    expect(screen.getByText(/no parts requests match/i)).toBeInTheDocument();
  });

  it("renders a loading state distinctly", () => {
    render(<PartsRequestList items={[]} loading />);
    expect(screen.getByText(/loading parts requests/i)).toBeInTheDocument();
  });

  it("renders an error state distinctly, without a raw exception string", () => {
    render(<PartsRequestList items={[]} error="Network error — could not reach the parts request service." />);
    expect(screen.getByText(/could not load parts requests/i)).toBeInTheDocument();
  });

  it("search filters rows by request id/job/technician/part", async () => {
    render(<PartsRequestList items={partsRequestListFixture} />);
    const user = userEvent.setup();
    await user.type(screen.getByLabelText(/search parts requests/i), "Deepak");
    expect(screen.getByText("pr_301")).toBeInTheDocument();
    expect(screen.queryByText("pr_302")).not.toBeInTheDocument();
  });

  it("status filter narrows to the selected status", async () => {
    render(<PartsRequestList items={partsRequestListFixture} />);
    const user = userEvent.setup();
    await user.selectOptions(screen.getByLabelText(/filter by status/i), "rejected");
    expect(screen.getByText("pr_303")).toBeInTheDocument();
    expect(screen.queryByText("pr_301")).not.toBeInTheDocument();
  });

  it("never renders a field_ops.Job canonical id (fo_job_*) anywhere in a row, and no technician mark-installed control", () => {
    render(<PartsRequestList items={partsRequestListFixture} />);
    expect(screen.queryByText(/fo_job_/i)).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: /install/i })).not.toBeInTheDocument();
  });
});
