import React from "react";
import { render, screen, fireEvent, waitFor } from "@testing-library/react-native";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { SafeAreaProvider } from "react-native-safe-area-context";
import { ThemeProvider } from "../../../design-system/themes";
import { JobTimelineScreen } from "../JobTimelineScreen";

const TEST_INSETS = { frame: { x: 0, y: 0, width: 0, height: 0 }, insets: { top: 0, left: 0, right: 0, bottom: 0 } };

jest.mock("../../../services/jobDetail/jobDetailApi");
import * as jobDetailApi from "../../../services/jobDetail/jobDetailApi";

const mockGoBack = jest.fn();
const navigation = { goBack: mockGoBack } as any;
const route = { params: { jobId: "j1", jobReference: "HS-1044" } } as any;

function renderScreen() {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <SafeAreaProvider initialMetrics={TEST_INSETS}>
      <QueryClientProvider client={client}>
        <ThemeProvider><JobTimelineScreen route={route} navigation={navigation} /></ThemeProvider>
      </QueryClientProvider>
    </SafeAreaProvider>,
  );
}

beforeEach(() => jest.clearAllMocks());

describe("JobTimelineScreen (spec section 15)", () => {
  it("renders only real backend timeline entries, no fabricated history", async () => {
    (jobDetailApi.getJobTimeline as jest.Mock).mockResolvedValue({
      ok: true,
      data: { job_id: "j1", entries: [{ event_type: "job.accepted", label: "Job accepted", notes: null, created_at: "2026-07-31T05:00:00Z" }], server_timestamp: "2026-07-31T05:05:00Z" },
    });
    renderScreen();
    expect(await screen.findByText("Job accepted")).toBeTruthy();
  });

  it("shows an empty state when there are no events yet", async () => {
    (jobDetailApi.getJobTimeline as jest.Mock).mockResolvedValue({ ok: true, data: { job_id: "j1", entries: [], server_timestamp: "2026-07-31T05:05:00Z" } });
    renderScreen();
    expect(await screen.findByText("No activity yet")).toBeTruthy();
  });

  it("goes back to Job Detail", async () => {
    (jobDetailApi.getJobTimeline as jest.Mock).mockResolvedValue({ ok: true, data: { job_id: "j1", entries: [], server_timestamp: "x" } });
    renderScreen();
    fireEvent.press(screen.getByLabelText("Back"));
    expect(mockGoBack).toHaveBeenCalled();
  });
});
