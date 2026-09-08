import React from "react";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, expect, it, vi } from "vitest";

const api = vi.hoisted(() => ({ status: vi.fn(), createOrder: vi.fn(), open: vi.fn(), confirm: vi.fn() }));
vi.mock("../../../../../../lib/api-topup", () => ({ topupApi: { status: api.status, createOrder: api.createOrder }, inr: (n: number) => `INR ${n}` }));
vi.mock("../../../../../../lib/api", () => ({ activationPaymentApi: { confirmFunding: api.confirm } }));
vi.mock("../../../../../../hooks/useRazorpayCheckout", () => ({ useRazorpayCheckout: () => ({ open: api.open }) }));
vi.mock("../../../../../../components/onboarding/OnboardingShell", () => ({ OnboardingShell: ({ children }: { children: React.ReactNode }) => <div>{children}</div> }));
import TechnicianPlanPage from "./page";

beforeEach(() => vi.clearAllMocks());

it("purchases the chosen plan and confirms payment before refreshing seats", async () => {
  const plan = { id: "three-seat-plan", name: "Team", seats: 3, credited_amount: 2000, gst_amount: 360, total_amount: 2360, validity_days: 30, is_default: true };
  api.status.mockResolvedValue({ plans: [plan], entitled_seats: 0, used_seats: 0, available_seats: 0, checkout_configured: true });
  api.createOrder.mockResolvedValue({ key: "test-key", order_id: "order_test", amount_paise: 236000, currency: "INR" });
  api.open.mockResolvedValue({ razorpay_order_id: "order_test", razorpay_payment_id: "payment_test", razorpay_signature: "test-signature" });
  api.confirm.mockResolvedValue({ status: "captured" });
  render(<TechnicianPlanPage />);
  fireEvent.click(await screen.findByRole("button", { name: "Buy this plan" }));
  expect(screen.getByText("30 days")).toBeInTheDocument();
  expect(screen.getByRole("heading", { name: "Team — 3 seats" })).toBeInTheDocument();
  expect(screen.getByText("Recommended")).toBeInTheDocument();
  await waitFor(() => expect(api.createOrder).toHaveBeenCalledWith("three-seat-plan"));
  await waitFor(() => expect(api.confirm).toHaveBeenCalledWith({ razorpay_order_id: "order_test", razorpay_payment_id: "payment_test", razorpay_signature: "test-signature" }));
  expect(api.status).toHaveBeenCalledTimes(2);
  expect(screen.getByText("Staff members")).toBeInTheDocument();
  expect(screen.getByText("Free")).toBeInTheDocument();
});

it("explains disabled checkout before the provider clicks when Admin has not configured Razorpay", async () => {
  const plan = { id: "starter", name: "Starter", seats: 3, credited_amount: 5000, gst_amount: 900, total_amount: 5900, validity_days: 0, is_default: true };
  api.status.mockResolvedValue({ plans: [plan], entitled_seats: 0, used_seats: 0, available_seats: 0, checkout_configured: false });
  render(<TechnicianPlanPage />);
  expect(await screen.findByRole("alert")).toHaveTextContent("administrator must save, test, and enable the Razorpay test Key ID and Key Secret");
  expect(screen.getByRole("button", { name: "Buy this plan" })).toBeDisabled();
  expect(api.createOrder).not.toHaveBeenCalled();
});
