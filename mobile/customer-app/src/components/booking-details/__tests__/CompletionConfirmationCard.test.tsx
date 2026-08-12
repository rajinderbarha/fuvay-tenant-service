import React from "react";
import { fireEvent } from "@testing-library/react-native";
import { renderWithProviders } from "../../../testing/renderWithProviders";
import { CompletionConfirmationCard } from "../CompletionConfirmationCard";
import { CustomerDirectPayment, CustomerHandover } from "../../../api/contracts/customerClosure";

const handover: CustomerHandover = {
  job_id: "job-1", status: "requested", requested_at: "2026-08-12T10:00:00Z", can_acknowledge: true,
};
const payment: CustomerDirectPayment = {
  payment_id: "pay-1", job_id: "job-1", booking_id: "booking-1", job_ref: "JOB-1",
  provider_business: "Acme Home Services", service_amount: "1200.00", currency: "INR",
  method: "Cash", payment_date: "2026-08-12T10:10:00Z", evidence_available: false,
  status: "awaiting_customer", customer_confirmed: false,
  customer_action: null,
  notice: "You paid this amount directly to the provider.",
};

function renderCard(overrides: Partial<React.ComponentProps<typeof CompletionConfirmationCard>> = {}) {
  const props: React.ComponentProps<typeof CompletionConfirmationCard> = {
    handover, payment: null, busy: false, failed: false,
    onAcknowledge: jest.fn(), onConfirmPayment: jest.fn(), onReportNotPaid: jest.fn(),
    ...overrides,
  };
  return { ...renderWithProviders(<CompletionConfirmationCard {...props} />), props };
}

describe("CompletionConfirmationCard", () => {
  it("lets the customer acknowledge a requested handover", () => {
    const { getByText, props } = renderCard();
    fireEvent.press(getByText("Confirm handover"));
    expect(props.onAcknowledge).toHaveBeenCalledTimes(1);
  });

  it("shows backend-recorded payment data and both customer decisions", () => {
    const acknowledged = { ...handover, status: "acknowledged" as const, can_acknowledge: false };
    const { getByText, props } = renderCard({ handover: acknowledged, payment });
    expect(getByText("Acme Home Services recorded INR 1200.00 paid by Cash. ServiceOS did not collect this money.")).toBeTruthy();
    fireEvent.press(getByText("Yes, I paid INR 1200.00"));
    fireEvent.press(getByText("I did not make this payment"));
    expect(props.onReportNotPaid).not.toHaveBeenCalled();
    fireEvent.press(getByText("Confirm payment issue"));
    expect(props.onConfirmPayment).toHaveBeenCalledTimes(1);
    expect(props.onReportNotPaid).toHaveBeenCalledTimes(1);
  });

  it("stays hidden before the technician requests handover", () => {
    const { queryByText } = renderCard({
      handover: { ...handover, status: "not_requested", can_acknowledge: false }, payment: null,
    });
    expect(queryByText("Confirm service handover")).toBeNull();
  });

  it("keeps an already-reported mismatch read-only", () => {
    const acknowledged = { ...handover, status: "acknowledged" as const, can_acknowledge: false };
    const { getByText, queryByText } = renderCard({
      handover: acknowledged,
      payment: { ...payment, status: "mismatched", customer_action: "not_paid" },
    });
    expect(getByText("Payment issue reported")).toBeTruthy();
    expect(queryByText("Yes, I paid INR 1200.00")).toBeNull();
  });

  it("still asks the customer when only the provider amount triggered the mismatch", () => {
    const acknowledged = { ...handover, status: "acknowledged" as const, can_acknowledge: false };
    const { getByText } = renderCard({
      handover: acknowledged,
      payment: { ...payment, status: "mismatched", customer_action: null },
    });
    expect(getByText("Yes, I paid INR 1200.00")).toBeTruthy();
  });
});
