import React from "react";
import { Appearance } from "react-native";
import { render, screen, fireEvent, waitFor } from "@testing-library/react-native";
import { ThemeProvider } from "../../context/ThemeContext";
import { JobDetailScreen } from "../JobDetailScreen";
import { jobsApi } from "../../lib/api";

// UX-05B item 2 regression coverage: JobDetailScreen holds the real
// money-collection ("Complete Job") modal -- work_summary + collected_amount
// -> jobsApi.complete(). This is the dedicated coverage the Round 7 deferral
// called for before converting the screen to reactive theme colors, added
// alongside (not after) that conversion.

jest.mock("../../lib/api", () => {
  const actual = jest.requireActual("../../lib/api");
  return {
    ...actual,
    jobsApi: {
      ...actual.jobsApi,
      get: jest.fn(),
      complete: jest.fn(),
    },
  };
});

const mockJobDetail = {
  job: {
    id: "job-1", job_number: "L501-JOB-0001", booking_id: "booking-1", tenant_id: "t1",
    customer_id: "c1", assigned_staff_id: "s1",
    scheduled_date: "2026-07-20", scheduled_time_window: "10:00-12:00",
    city: "Ludhiana", zipcode: "141001",
    status: "work_done", assignment_status: "accepted", failure_reason: null,
    completion_data: null, created_at: "2026-07-11T00:00:00Z", updated_at: "2026-07-11T00:00:00Z",
  },
  assignment: null,
  booking: {
    id: "booking-1", booking_number: "BK-1", customer_name: "Test Customer",
    city: "Ludhiana", zipcode: "141001", preferred_date: null, preferred_time_window: null,
    issue_summary: "AC not cooling",
  },
};

function renderScreen(scheme: "light" | "dark") {
  jest.spyOn(Appearance, "getColorScheme").mockReturnValue(scheme);
  const navigation = {} as never;
  const route = { params: { jobId: "job-1" }, key: "JobDetail", name: "JobDetail" as const };
  return render(
    <ThemeProvider>
      <JobDetailScreen navigation={navigation} route={route as never} />
    </ThemeProvider>
  );
}

describe("JobDetailScreen -- money-collection modal", () => {
  jest.setTimeout(15000);
  beforeEach(() => {
    jest.clearAllMocks();
    (jobsApi.get as jest.Mock).mockResolvedValue(mockJobDetail);
    (jobsApi.complete as jest.Mock).mockResolvedValue({ ...mockJobDetail.job, status: "completed" });
  });

  it("opens the Complete Job modal and submits work_summary + collected_amount (light theme)", async () => {
    renderScreen("light");
    await waitFor(() => expect(screen.getByText("L501-JOB-0001")).toBeTruthy());

    fireEvent.press(screen.getByText("Complete & Submit"));
    expect(screen.getByText("Complete Job")).toBeTruthy();

    fireEvent.changeText(screen.getByPlaceholderText(/AC unit cleaned/), "Replaced compressor capacitor.");
    fireEvent.changeText(screen.getByPlaceholderText(/Amount Collected/), "1500");
    fireEvent.press(screen.getByText("Submit & Complete"));

    await waitFor(() => expect(jobsApi.complete).toHaveBeenCalledWith(
      "job-1", "Replaced compressor capacitor.", 1500
    ));
  });

  it("opens the Complete Job modal and displays amounts correctly (dark theme)", async () => {
    renderScreen("dark");
    await waitFor(() => expect(screen.getByText("L501-JOB-0001")).toBeTruthy());

    fireEvent.press(screen.getByText("Complete & Submit"));
    fireEvent.changeText(screen.getByPlaceholderText(/AC unit cleaned/), "Filter replaced.");
    fireEvent.changeText(screen.getByPlaceholderText(/Amount Collected/), "2500");
    fireEvent.press(screen.getByText("Submit & Complete"));

    await waitFor(() => expect(jobsApi.complete).toHaveBeenCalledWith("job-1", "Filter replaced.", 2500));
  });

  it("renders a real completed job's collected amount correctly (₹ formatting)", async () => {
    (jobsApi.get as jest.Mock).mockResolvedValue({
      ...mockJobDetail,
      job: {
        ...mockJobDetail.job, status: "completed",
        completion_data: { work_summary: "Done.", collected_amount: 3200 },
      },
    });
    renderScreen("light");
    await waitFor(() => expect(screen.getByText(/3,200 collected/)).toBeTruthy());
  });

  it("requires both work summary and collected amount before submitting", async () => {
    renderScreen("light");
    await waitFor(() => expect(screen.getByText("L501-JOB-0001")).toBeTruthy());
    fireEvent.press(screen.getByText("Complete & Submit"));
    fireEvent.press(screen.getByText("Submit & Complete"));
    // jobsApi.complete must not fire with missing required fields.
    expect(jobsApi.complete).not.toHaveBeenCalled();
  });
});
