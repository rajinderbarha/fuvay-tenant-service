import React from "react";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, expect, it, vi } from "vitest";

const api = vi.hoisted(() => ({ status: vi.fn(), createOrder: vi.fn(), open: vi.fn(), confirm: vi.fn(), reconcile: vi.fn() }));
vi.mock("../../../../../../lib/api-topup", async importOriginal => ({
  ...await importOriginal<typeof import("../../../../../../lib/api-topup")>(),
  topupApi: { status: api.status, createOrder: api.createOrder }, inr: (n: number) => `INR ${n}`,
}));
vi.mock("../../../../../../lib/api", () => ({ activationPaymentApi: { confirmFunding: api.confirm, reconcileFunding: api.reconcile } }));
vi.mock("../../../../../../hooks/useRazorpayCheckout", () => ({ useRazorpayCheckout: () => ({ open: api.open }) }));
vi.mock("../../../../../../components/onboarding/OnboardingShell", () => ({ OnboardingShell: ({ children }: { children: React.ReactNode }) => <div>{children}</div> }));
import TechnicianPlanPage from "./page";

beforeEach(() => vi.resetAllMocks());

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

it.each(["checkout", "confirmation"])("recovers a captured payment after an Invalid Token error during %s", async stage => {
  const plan = { id: "starter", name: "Starter", seats: 3, credited_amount: 5000, gst_amount: 900, total_amount: 5900 };
  const initial = { plans: [plan], entitled_seats: 0, used_seats: 0, available_seats: 0, checkout_configured: true };
  api.status.mockResolvedValueOnce(initial).mockResolvedValue({ ...initial, entitled_seats: 3, available_seats: 3, credit_balance: 5000 });
  api.createOrder.mockResolvedValue({ key: "test-key", order_id: "order_existing", amount_paise: 590000, currency: "INR" });
  if (stage === "checkout") api.open.mockRejectedValue(new Error("Invalid Token"));
  else {
    api.open.mockResolvedValue({ razorpay_order_id: "order_existing", razorpay_payment_id: "pay_test", razorpay_signature: "signed" });
    api.confirm.mockRejectedValue(new Error("Invalid Token"));
  }
  api.reconcile.mockResolvedValue({ status: "captured", captured: true });
  const updated = vi.fn();
  window.addEventListener("home-services-credit-updated", updated);
  render(<TechnicianPlanPage/>);
  fireEvent.click(await screen.findByRole("button", { name: "Buy this plan" }));
  expect(await screen.findByRole("link", { name: /Continue to team setup/ })).toBeInTheDocument();
  expect(api.reconcile).toHaveBeenCalledExactlyOnceWith("order_existing");
  expect(api.createOrder).toHaveBeenCalledOnce();
  expect(screen.queryByText("Invalid Token")).not.toBeInTheDocument();
  await waitFor(() => expect(updated).toHaveBeenCalledOnce());
  window.removeEventListener("home-services-credit-updated", updated);
});

it("does not unlock seats when Razorpay has not captured payment", async () => {
  api.status.mockResolvedValue({ plans: [{ id: "starter", name: "Starter", seats: 3, credited_amount: 5000, gst_amount: 900, total_amount: 5900 }], entitled_seats: 0, checkout_configured: true });
  api.createOrder.mockResolvedValue({ order_id: "order_unpaid" });
  api.open.mockRejectedValue(new Error("Invalid Token"));
  api.reconcile.mockResolvedValue({ status: "created", captured: false });
  render(<TechnicianPlanPage/>);
  fireEvent.click(await screen.findByRole("button", { name: "Buy this plan" }));
  expect(await screen.findByRole("alert")).toHaveTextContent("Invalid Token");
  expect(screen.queryByRole("link", { name: /Continue to team setup/ })).not.toBeInTheDocument();
  expect(api.confirm).not.toHaveBeenCalled();
});

it("uses an already recovered payment without opening checkout again", async () => {
  api.status.mockResolvedValue({ plans: [{ id: "starter", name: "Starter", seats: 3, credited_amount: 5000, gst_amount: 900, total_amount: 5900 }], entitled_seats: 3, available_seats: 3, checkout_configured: true });
  api.createOrder.mockResolvedValue({ order_id: "order_paid", already_confirmed: true });
  render(<TechnicianPlanPage/>);
  fireEvent.click(await screen.findByRole("button", { name: "Buy this plan" }));
  expect(await screen.findByText("Payment confirmed. Your technician seats and usage credit are ready.")).toBeInTheDocument();
  expect(api.open).not.toHaveBeenCalled();
  expect(api.confirm).not.toHaveBeenCalled();
});
