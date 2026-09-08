import React from "react";
import { cleanup, fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { afterEach, beforeEach, expect, it, vi } from "vitest";
import DirectPaymentsPage from "./page";

const state = vi.hoisted(() => ({ query: "", push: vi.fn(), list: vi.fn(), get: vi.fn() }));
vi.mock("next/navigation", () => ({ useRouter: () => ({ push: state.push }), useSearchParams: () => new URLSearchParams(state.query) }));
vi.mock("../../../../lib/api", () => ({
  API_BASE: "", getToken: () => null, ServiceOSError: class extends Error {},
  homeServicesDirectPaymentsApi: { list: state.list, get: state.get },
}));
const queue = () => ({
  summary: {
    awaiting_provider: {count: 3, amount: "0"}, awaiting_customer: {count: 0, amount: "0"},
    confirmed: {count: 0, amount: "0"}, mismatched: {count: 0, amount: "0"}, disputed: {count: 0, amount: "0"},
    confirmed_direct_payment_value: {label: "Confirmed direct-payment value", amount: "0", currency: "INR", subtext: "Total confirmed amount"},
  },
  tab_counts: {needs_action: 3, all: 3, confirmed: 0, mismatch: 0, disputed: 0},
  filters: {statuses: [{value: "confirmed", label: "Confirmed"}], methods: [{value: "onsite_upi", label: "UPI"}],
    services: [{value: "service1", label: "Geyser Service & Descaling"}], technicians: [{value: "tech1", label: "Technician"}]},
  pagination: {page: 1, pages: 1, total: 3},
  records: [7,8,9].map(n => ({id: `job:${n}`, kind: "job", job_ref: `BAS-JOB-000${n}`, job_id: String(n), time_window: "14:00-16:00",
    customer_alias: "Customer HS-9E8A", service: "Geyser Service & Descaling", expected_amount: "999", declared_amount: null,
    currency: "INR", method_label: null, provider_confirmation: {state: "pending"}, customer_confirmation: {state: "pending"},
    status: "awaiting_provider", status_label: "Awaiting provider", updated_at: new Date().toISOString()})),
});
beforeEach(() => { vi.resetAllMocks(); state.query = ""; state.list.mockResolvedValue(queue()); });
afterEach(cleanup);

it("renders the reference queue with actual counts and no automatic detail selection", async () => {
  render(<DirectPaymentsPage/>);
  const row = await screen.findByRole("button", {name: "View payment for BAS-JOB-0007"});
  expect(screen.getByRole("heading", {name: "Direct payments"})).toBeInTheDocument();
  expect(screen.getByRole("button", {name: "Needs action 3"})).toHaveAttribute("aria-pressed", "true");
  expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
  expect(state.push).not.toHaveBeenCalled();
  expect(within(row).queryByText("₹999")).not.toBeInTheDocument();
  expect(within(row).getByText("Declared").parentElement).toHaveTextContent("Declared—");
  fireEvent.click(row);
  expect(state.push).toHaveBeenCalledWith("/home-services/direct-payments?payment_id=job%3A7");
});

it.each([["Payment method", "onsite_upi", "method"], ["Service", "service1", "service_id"], ["Technician", "tech1", "technician_id"], ["Payment status", "confirmed", "status"]])("connects the %s filter to the existing queue API parameters", async (label, value, key) => {
  state.query = "q=geyser&page=2";
  render(<DirectPaymentsPage/>); await screen.findByRole("button", {name: "View payment for BAS-JOB-0007"});
  fireEvent.change(screen.getByRole("combobox", {name: label}), {target: {value}});
  const params = new URL(state.push.mock.calls.at(-1)![0], "http://localhost").searchParams;
  expect(params.get(key)).toBe(value); expect(params.get("q")).toBe("geyser"); expect(params.get("page")).toBe("1");
});

it("keeps search and queue tabs URL-addressable", async () => {
  render(<DirectPaymentsPage/>); await screen.findByRole("button", {name: "Needs action 3"});
  const input = screen.getByRole("textbox", {name: "Search job, customer or service"});
  fireEvent.change(input, {target: {value: "BAS-JOB-0007"}}); fireEvent.keyDown(input, {key: "Enter"});
  expect(state.push).toHaveBeenLastCalledWith("/home-services/direct-payments?q=BAS-JOB-0007&page=1");
  fireEvent.click(screen.getByRole("button", {name: "Confirmed 0"}));
  expect(state.push).toHaveBeenLastCalledWith("/home-services/direct-payments?status=confirmed&page=1");
});

it("opens an undeclared job in a dismissible dialog with a link to record payment", async () => {
  state.query = "payment_id=job%3A7"; render(<DirectPaymentsPage/>);
  const dialog = await screen.findByRole("dialog", {name: "Payment details"});
  expect(await within(dialog).findByRole("link", {name: "Open job to record payment"})).toHaveAttribute("href", "/home-services/bookings-jobs?job_id=7");
  expect(state.get).not.toHaveBeenCalled();
  fireEvent.keyDown(document, {key: "Escape"});
  expect(state.push).toHaveBeenLastCalledWith("/home-services/direct-payments");
});

it("shows a retryable detail error without losing the payment queue", async () => {
  state.query = "payment_id=payment1"; state.get.mockRejectedValue(new Error("Offline"));
  render(<DirectPaymentsPage/>);
  const retry = await screen.findByRole("button", {name: "Retry"}); fireEvent.click(retry);
  await waitFor(() => expect(state.get).toHaveBeenCalledTimes(2));
  expect(screen.getByRole("button", {name: "View payment for BAS-JOB-0007"})).toBeInTheDocument();
});

it("does not invent zero summary cards on API failure", async () => {
  state.list.mockRejectedValue(new Error("Offline")); render(<DirectPaymentsPage/>);
  expect(await screen.findByRole("alert")).toHaveTextContent("We couldn't load direct payments.");
  expect(screen.queryByText("₹0")).not.toBeInTheDocument();
});
