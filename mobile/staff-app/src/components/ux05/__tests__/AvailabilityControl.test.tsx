import React from "react";
import { render, screen, fireEvent } from "@testing-library/react-native";
import { AvailabilityControl } from "../AvailabilityControl";
import { NetworkStatusBanner } from "../NetworkStatusBanner";

describe("AvailabilityControl", () => {
  it("calls onChange with the selected work status when a chip is pressed", () => {
    const onChange = jest.fn();
    render(<AvailabilityControl
      availability={{ meta:{readiness:"mock_design_only"}, workStatus:"available", accountStatus:"active", currentJobStatus:null }}
      onChange={onChange}
    />);
    fireEvent.press(screen.getByText("Busy"));
    expect(onChange).toHaveBeenCalledWith("busy");
  });

  it("shows account status and current job status as distinct fields from work status", () => {
    render(<AvailabilityControl
      availability={{ meta:{readiness:"mock_design_only"}, workStatus:"on_job", accountStatus:"active", currentJobStatus:"reached_site" }}
      onChange={() => {}}
    />);
    expect(screen.getByText("active")).toBeTruthy();
    expect(screen.getByText("reached_site")).toBeTruthy();
  });
});

describe("NetworkStatusBanner", () => {
  it("renders nothing when online and idle (the default, non-intrusive state)", () => {
    render(<NetworkStatusBanner state={{ meta:{readiness:"mock_design_only"}, networkState:"online", cacheState:"fresh", pendingDrafts:0, syncState:"idle" }} />);
    expect(screen.queryByTestId("network-status-banner")).toBeNull();
  });

  it("renders an offline-specific message when offline", () => {
    render(<NetworkStatusBanner state={{ meta:{readiness:"mock_design_only"}, networkState:"offline", cacheState:"stale_cached", pendingDrafts:0, syncState:"idle" }} />);
    expect(screen.getByText(/offline/i)).toBeTruthy();
  });

  it("renders a pending-draft count when sync_pending", () => {
    render(<NetworkStatusBanner state={{ meta:{readiness:"mock_design_only"}, networkState:"online", cacheState:"fresh", pendingDrafts:3, syncState:"sync_pending" }} />);
    expect(screen.getByText(/3 drafts waiting to sync/i)).toBeTruthy();
  });
});
