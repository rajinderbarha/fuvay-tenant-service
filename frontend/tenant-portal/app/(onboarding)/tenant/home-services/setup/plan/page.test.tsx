import React from "react";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { expect, it, vi } from "vitest";

const api = vi.hoisted(() => ({ status: vi.fn(), createOrder: vi.fn(), open: vi.fn(), confirm: vi.fn() }));
vi.mock("../../../../../../lib/api-topup", () => ({ topupApi: { status: api.status, createOrder: api.createOrder }, inr: (n: number) => `INR ${n}` }));
vi.mock("../../../../../../lib/api", () => ({ activationPaymentApi: { confirmFunding: api.confirm } }));
vi.mock("../../../../../../hooks/useRazorpayCheckout", () => ({ useRazorpayCheckout: () => ({ open: api.open }) }));
vi.mock("../../../../../../components/onboarding/OnboardingShell", () => ({ OnboardingShell: ({ children }: { children: React.ReactNode }) => <div>{children}</div> }));
import TechnicianPlanPage from "./page";

it("purchases the chosen plan and confirms payment before refreshing seats", async () => {
  const plan = { id: "three-seat-plan", name: "Team", seats: 3, credited_amount: 2000, gst_amount: 360, total_amount: 2360, validity_days: 30, is_default: true };
  api.status.mockResolvedValue({ plans: [plan], entitled_seats: 0, used_seats: 0, available_seats: 0 });
  api.createOrder.mockResolvedValue({ key: "test-key", order_id: "order_test", amount_paise: 236000, currency: "INR" });
  api.open.mockResolvedValue({ razorpay_order_id: "order_test", razorpay_payment_id: "payment_test", razorpay_signature: "test-signature" });
  api.confirm.mockResolvedValue({ status: "captured" });
  render(<TechnicianPlanPage />);
  fireEvent.click(await screen.findByRole("button", { name: "Buy this plan" }));
  expect(screen.getByText("Validity: 30 days")).toBeInTheDocument();
  expect(screen.getByRole("heading", { name: "Team · Recommended" })).toBeInTheDocument();
  await waitFor(() => expect(api.createOrder).toHaveBeenCalledWith("three-seat-plan"));
  await waitFor(() => expect(api.confirm).toHaveBeenCalledWith({ razorpay_order_id: "order_test", razorpay_payment_id: "payment_test", razorpay_signature: "test-signature" }));
  expect(api.status).toHaveBeenCalledTimes(2);
  expect(screen.getByText("Staff members free", { exact: false })).toBeInTheDocument();
});
