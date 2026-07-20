import React from "react";
import { screen } from "@testing-library/react-native";
import { renderWithTheme as render } from "../../../testUtils/renderWithTheme";
import { PipelineBadge } from "../PipelineBadge";
import { PermissionRestrictedState } from "../PermissionRestrictedState";

describe("PipelineBadge (RNTL render smoke test)", () => {
  it("renders the source booking id, proving provenance is never collapsed into job id alone", () => {
    render(<PipelineBadge provenance={{ pipeline:"service_booking_service_job", sourceBookingId:"bk_abcdef12", jobId:"sj_1", jobModel:"ServiceJob" }} />);
    expect(screen.getByText(/bk_abcde/)).toBeTruthy();
  });

  it("renders a compact ServiceJob label without the booking id when compact=true", () => {
    render(<PipelineBadge compact provenance={{ pipeline:"service_booking_service_job", sourceBookingId:"bk_abcdef12", jobId:"sj_1", jobModel:"ServiceJob" }} />);
    expect(screen.getByText("ServiceJob")).toBeTruthy();
  });
});

describe("PermissionRestrictedState (RNTL render smoke test)", () => {
  it("renders the given reason text", () => {
    render(<PermissionRestrictedState reason="No grant for this account." />);
    expect(screen.getByText("No grant for this account.")).toBeTruthy();
  });

  it("renders a default reason when none is given", () => {
    render(<PermissionRestrictedState />);
    expect(screen.getByText(/do not have permission/)).toBeTruthy();
  });
});
