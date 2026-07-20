import { isQuoteActionable, quoteStatusTitleKey, selectPrimaryQuote } from "../quote-state";
import type { ValidatedQuote } from "../quote-schema";

function makeQuote(overrides: Partial<ValidatedQuote>): ValidatedQuote {
  return {
    id: "q1",
    quote_number: "QT-1",
    job_id: "job1",
    status: "sent_to_customer",
    quote_type: "additional_work_quote",
    currency: "INR",
    labour_amount: "0",
    parts_amount: "0",
    service_amount: "0",
    discount_amount: "0",
    tax_amount: "0",
    total_amount: "0",
    customer_payable_amount: "0",
    customer_visible_notes: null,
    rejection_reason: null,
    revision_reason: null,
    created_at: null,
    ...overrides,
  };
}

describe("isQuoteActionable", () => {
  it("is actionable only when status is sent_to_customer — the only status QUOTE_TRANSITIONS allows a customer decision from", () => {
    expect(isQuoteActionable(makeQuote({ status: "sent_to_customer" }))).toBe(true);
    for (const status of [
      "draft",
      "submitted_to_provider",
      "provider_approved",
      "customer_approved",
      "customer_rejected",
      "revision_requested",
      "revised",
      "expired",
      "cancelled",
    ]) {
      expect(isQuoteActionable(makeQuote({ status }))).toBe(false);
    }
  });
});

describe("quoteStatusTitleKey", () => {
  it("maps every real status to a distinct key", () => {
    expect(quoteStatusTitleKey("sent_to_customer")).toBe("quoteDecision.status.awaitingYourDecision");
    expect(quoteStatusTitleKey("customer_approved")).toBe("quoteDecision.status.approved");
    expect(quoteStatusTitleKey("customer_rejected")).toBe("quoteDecision.status.rejected");
  });

  it("fails safe on an unrecognized status", () => {
    expect(quoteStatusTitleKey("something_new")).toBe("quoteDecision.status.unknown");
  });
});

describe("selectPrimaryQuote", () => {
  it("returns null for an empty list", () => {
    expect(selectPrimaryQuote([])).toBeNull();
  });

  it("prefers the actionable (sent_to_customer) quote over a more recent non-actionable one", () => {
    const quotes = [makeQuote({ id: "newer", status: "draft" }), makeQuote({ id: "older-but-actionable", status: "sent_to_customer" })];
    expect(selectPrimaryQuote(quotes)?.id).toBe("older-but-actionable");
  });

  it("falls back to the first (most recent, per the server's created_at desc ordering) quote when none are actionable", () => {
    const quotes = [makeQuote({ id: "most-recent", status: "customer_approved" }), makeQuote({ id: "older", status: "customer_rejected" })];
    expect(selectPrimaryQuote(quotes)?.id).toBe("most-recent");
  });
});
