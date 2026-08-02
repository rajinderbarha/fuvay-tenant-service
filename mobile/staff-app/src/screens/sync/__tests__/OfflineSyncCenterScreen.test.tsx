import React from "react";
import { render, screen, fireEvent } from "@testing-library/react-native";
import { ThemeProvider } from "../../../design-system/themes";
import { OfflineSyncCenterScreen } from "../OfflineSyncCenterScreen";
import { QueueItem } from "../../../services/sync/types";

jest.mock("../useSyncCenter");
import { useSyncCenter } from "../useSyncCenter";

const mockNavigate = jest.fn();
const navigation = { navigate: mockNavigate, goBack: jest.fn() } as any;
const route = { params: undefined } as any;

function item(overrides: Partial<QueueItem>): QueueItem {
  return {
    local_id: "1", operation_type: "WORK_START", operation_class: "IDEMPOTENT_MUTATION",
    session_generation: 1, tenant_id: "t1", vertical_code: "home_services",
    idempotency_key: "k", dependencies: [], state: "waiting", attempt_count: 0,
    next_attempt_at: null, created_at: "2026-07-30T00:00:00Z", updated_at: "2026-07-30T00:00:00Z",
    title: "Inspection photos", job_reference: "HS-1044 · AC Repair", payload: {},
    ...overrides,
  };
}

function baseReturn(overrides: Partial<ReturnType<typeof useSyncCenter>> = {}) {
  const syncingNow = [item({ local_id: "s1", state: "uploading", title: "Inspection photos" })];
  const waiting = [item({ local_id: "w1", state: "waiting", title: "Part request" })];
  const needsAttention = [item({ local_id: "c1", state: "conflict", title: "Estimate draft conflict" })];
  const recentlySynced = [item({ local_id: "r1", state: "server_confirmed", title: "Payment confirmation" })];
  return {
    items: [...syncingNow, ...waiting, ...needsAttention, ...recentlySynced],
    metrics: { synced: 12, uploading: 2, waiting: 1, failed: 1 },
    filter: "all" as const, setFilter: jest.fn(),
    filteredCounts: { all: 16, pending: 3, failed: 1 },
    syncingNow, waiting, needsAttention, recentlySynced,
    connectionState: "online" as const, isSyncing: false,
    syncAllNow: jest.fn().mockResolvedValue({ attempted: 0, confirmed: 0, failed: 0, conflicted: 0, skipped: 0 }),
    removeItem: jest.fn(), refresh: jest.fn(), lastSyncedAt: new Date().toISOString(),
    ...overrides,
  };
}

function renderScreen() {
  return render(<ThemeProvider><OfflineSyncCenterScreen route={route} navigation={navigation} /></ThemeProvider>);
}

beforeEach(() => jest.clearAllMocks());

describe("OfflineSyncCenterScreen (Phase Z)", () => {
  it("shows the real connection state and metrics", () => {
    (useSyncCenter as jest.Mock).mockReturnValue(baseReturn());
    renderScreen();
    expect(screen.getByText("You're online")).toBeTruthy();
    expect(screen.getByText("12")).toBeTruthy();
  });

  it("shows all four groups with real, non-fabricated titles", () => {
    (useSyncCenter as jest.Mock).mockReturnValue(baseReturn());
    renderScreen();
    expect(screen.getByText("Syncing now")).toBeTruthy();
    expect(screen.getAllByText("Waiting").length).toBeGreaterThan(0);
    expect(screen.getByText("Needs attention")).toBeTruthy();
    expect(screen.getByText("Recently synced")).toBeTruthy();
    expect(screen.getByText("Estimate draft conflict")).toBeTruthy();
  });

  it("navigates to conflict review for a conflicted item, not the generic detail screen", () => {
    (useSyncCenter as jest.Mock).mockReturnValue(baseReturn());
    renderScreen();
    fireEvent.press(screen.getByText("Review"));
    expect(mockNavigate).toHaveBeenCalledWith("SyncConflictReview", { localId: "c1" });
  });

  it("navigates to item detail for a non-conflict row", () => {
    (useSyncCenter as jest.Mock).mockReturnValue(baseReturn());
    renderScreen();
    fireEvent.press(screen.getByText("Part request"));
    expect(mockNavigate).toHaveBeenCalledWith("SyncItemDetail", { localId: "w1" });
  });

  it("disables Sync all now while a pass is already in progress", () => {
    const syncAllNow = jest.fn().mockResolvedValue(null);
    (useSyncCenter as jest.Mock).mockReturnValue(baseReturn({ syncAllNow, isSyncing: true }));
    renderScreen();
    expect(screen.getByRole("button", { name: "Sync all now" }).props.accessibilityState?.disabled).toBe(true);
  });

  it("calls syncAllNow when the footer button is pressed", () => {
    const syncAllNow = jest.fn().mockResolvedValue(null);
    (useSyncCenter as jest.Mock).mockReturnValue(baseReturn({ syncAllNow }));
    renderScreen();
    fireEvent.press(screen.getByRole("button", { name: "Sync all now" }));
    expect(syncAllNow).toHaveBeenCalled();
  });

  it("never shows a fabricated 'Completed'/'Approved' label for a local item", () => {
    (useSyncCenter as jest.Mock).mockReturnValue(baseReturn());
    renderScreen();
    expect(screen.queryByText("Completed")).toBeNull();
    expect(screen.queryByText("Approved")).toBeNull();
  });

  it("shows an empty state when the queue is empty", () => {
    (useSyncCenter as jest.Mock).mockReturnValue(baseReturn({
      items: [], syncingNow: [], waiting: [], needsAttention: [], recentlySynced: [],
      metrics: { synced: 0, uploading: 0, waiting: 0, failed: 0 }, filteredCounts: { all: 0, pending: 0, failed: 0 },
    }));
    renderScreen();
    expect(screen.getByText("Nothing pending")).toBeTruthy();
  });

  it("navigates to Offline Storage from the footer link", () => {
    (useSyncCenter as jest.Mock).mockReturnValue(baseReturn());
    renderScreen();
    fireEvent.press(screen.getByText("Manage storage"));
    expect(mockNavigate).toHaveBeenCalledWith("OfflineStorage");
  });
});
