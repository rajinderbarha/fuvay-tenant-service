import { fireEvent, render, screen, waitFor, cleanup } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import CoveragePage from "../../../app/(onboarding)/tenant/home-services/setup/coverage-availability/page";
import { dayError, scheduleDraft, businessDate } from "../../../lib/coverage-schedule";
import { twoHourWindows, allocateDailySlots } from "../../../lib/booking-capacity";

const api = vi.hoisted(() => ({ save: vi.fn(), list: vi.fn(), preview: vi.fn(), push: vi.fn(), createException: vi.fn() }));
vi.mock("next/navigation", () => ({ useRouter: () => ({ push: api.push }), usePathname: () => "/tenant/home-services/setup/coverage-availability" }));
vi.mock("../../onboarding/OnboardingShell", () => ({ OnboardingShell: ({ children }: any) => <div>{children}</div> }));
vi.mock("../../layout/TenantLayout", () => ({ TenantLayout: ({ children }: any) => <div>{children}</div> }));
vi.mock("../../../lib/api-topup", () => ({ topupApi: { status: async () => ({ entitled_seats: 3, used_seats: 3 }) } }));
vi.mock("../../../lib/api", () => ({
  ServiceOSError: class extends Error {},
  providerServiceAreasApi: { list: async () => ({ areas: [{ id: "area", coverage_type: "zipcode", zipcode: "110001", is_active: true }] }) },
  providerAvailabilityApi: { list: api.list, saveSchedule: api.save, slotPreview: api.preview },
  bookingWindowApi: { get: async () => ({ minimum_notice_minutes: 120, maximum_advance_booking_days: 7, buffer_minutes_between_jobs: 0, slot_duration_minutes: 120, allow_same_day_booking: true, emergency_booking_allowed: false, timezone: "Asia/Kolkata" }) },
  availabilityExceptionsApi: { list: async () => ({ exceptions: [] }), create: api.createException },
}));

const rule = { id: "monday", tenant_id: "tenant", scope_type: "provider", scope_id: null, day_of_week: 1,
  start_time: "09:00", end_time: "18:00", is_active: true, max_jobs_per_day: null } as any;

beforeEach(() => {
  vi.clearAllMocks();
  api.list.mockResolvedValue({ rules: [rule] });
  api.preview.mockResolvedValue({ slots: [], closed: false, daily_remaining: 12 });
  api.save.mockImplementation(async (payload) => payload);
  Element.prototype.scrollIntoView = vi.fn();
});
afterEach(cleanup);

async function open() {
  render(<CoveragePage/>);
  return await screen.findByLabelText("Monday opening time");
}

describe("Coverage and availability editing", () => {
  it("keeps partial time edits local and saves all seven days and controls together", async () => {
    const input = await open();
    fireEvent.change(input, { target: { value: "" } });
    expect(input).toHaveValue("");
    expect(api.save).not.toHaveBeenCalled();
    fireEvent.change(input, { target: { value: "10:00" } });
    fireEvent.change(screen.getByLabelText("Monday closing time"), { target: { value: "19:00" } });
    fireEvent.change(screen.getByLabelText("Minimum notice (minutes)"), { target: { value: "180" } });
    expect(input).toHaveValue("10:00");
    expect(api.save).not.toHaveBeenCalled();
    fireEvent.click(screen.getByRole("button", { name: "Save draft" }));
    await waitFor(() => expect(api.save).toHaveBeenCalledTimes(1));
    const payload = api.save.mock.calls[0][0];
    expect(payload.rules).toHaveLength(7);
    expect(payload.rules[1]).toMatchObject({ start_time: "10:00", end_time: "19:00", is_active: true });
    expect(payload.booking_window).toMatchObject({ minimum_notice_minutes: 180, maximum_advance_booking_days: 7, buffer_minutes_between_jobs: 0 });
    await screen.findByText("No unsaved schedule changes");
  });

  it("keeps the draft and does not advance after a failed save", async () => {
    const input = await open();
    api.save.mockRejectedValueOnce(new Error("Schedule could not be saved"));
    fireEvent.change(input, { target: { value: "10:00" } });
    fireEvent.click(screen.getByRole("button", { name: "Save & continue" }));
    await screen.findByText("Schedule could not be saved");
    expect(input).toHaveValue("10:00");
    expect(api.push).not.toHaveBeenCalled();
  });

  it("retains edited hours when closing and reopening, and copies breaks and limits", async () => {
    await open();
    fireEvent.change(screen.getByLabelText("Monday opening time"), { target: { value: "08:00" } });
    fireEvent.change(screen.getByLabelText("Monday break start"), { target: { value: "12:00" } });
    fireEvent.change(screen.getByLabelText("Monday break end"), { target: { value: "13:00" } });
    fireEvent.change(screen.getByLabelText("Monday daily job limit"), { target: { value: "6" } });
    fireEvent.click(screen.getByLabelText("Monday open"));
    fireEvent.click(screen.getByLabelText("Monday open"));
    expect(screen.getByLabelText("Monday opening time")).toHaveValue("08:00");
    fireEvent.click(screen.getByRole("button", { name: "Copy Monday to weekdays" }));
    expect(screen.getByLabelText("Friday break start")).toHaveValue("12:00");
    expect(screen.getByLabelText("Friday daily job limit")).toHaveValue(6);
    expect(api.save).not.toHaveBeenCalled();
  });

  it("rejects daily limits beyond funded capacity and incomplete breaks before calling the server", async () => {
    await open();
    fireEvent.change(screen.getByLabelText("Monday daily job limit"), { target: { value: "13" } });
    fireEvent.click(screen.getByRole("button", { name: "Save draft" }));
    expect(api.save).not.toHaveBeenCalled();
    expect(screen.getAllByText(/Daily limit must be 1–12/).length).toBeGreaterThan(0);
    fireEvent.change(screen.getByLabelText("Monday daily job limit"), { target: { value: "" } });
    fireEvent.change(screen.getByLabelText("Monday break start"), { target: { value: "12:00" } });
    fireEvent.click(screen.getByRole("button", { name: "Save draft" }));
    expect(api.save).not.toHaveBeenCalled();
    expect(screen.getAllByText(/Enter both break times/).length).toBeGreaterThan(0);
  });

  it("discards draft changes without a network save", async () => {
    const input = await open();
    fireEvent.change(input, { target: { value: "10:00" } });
    fireEvent.click(screen.getByRole("button", { name: "Discard edits" }));
    expect(input).toHaveValue("09:00");
    expect(api.save).not.toHaveBeenCalled();
  });
});

describe("Schedule capacity helpers", () => {
  it("uses the active rule rather than an inactive duplicate", () => {
    expect(scheduleDraft([rule, { ...rule, id: "old", is_active: false, start_time: "12:00" }])[1].start_time).toBe("09:00");
  });
  it("retains closed-day times and normalizes API seconds", () => {
    expect(scheduleDraft([{ ...rule, is_active: false, start_time: "10:00:00" }])[1]).toMatchObject({ start_time: "10:00", is_active: false });
  });
  it("matches two-hour slots with breaks and travel time", () => {
    expect(twoHourWindows("09:00", "18:00", "13:00", "14:00", 30)).toEqual(["09:00–11:00", "14:00–16:00"]);
    const windows = twoHourWindows("09:00", "18:00");
    expect(allocateDailySlots(windows, 3, 6).map(s => s.capacity)).toEqual([2, 2, 1, 1]);
    expect(dayError({ ...scheduleDraft([rule])[1], max_jobs_per_day: "12" }, 3, 30)).toContain("1–9");
  });
  it("uses the business timezone for dates near midnight", () => {
    expect(businessDate("Asia/Kolkata", new Date("2026-09-08T20:00:00Z"))).toBe("2026-09-09");
  });
});
