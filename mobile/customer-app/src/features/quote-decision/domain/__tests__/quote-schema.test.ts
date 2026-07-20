import { parseQuoteList, parseQuoteDetail, toNumber } from "../quote-schema";

const validQuote = {
  id: "q1",
  quote_number: "QT-ABC123",
  job_id: "job1",
  status: "sent_to_customer",
  quote_type: "additional_work_quote",
  currency: "INR",
  labour_amount: "500.00",
  parts_amount: "1200.00",
  service_amount: "0.00",
  discount_amount: "0.00",
  tax_amount: "0.00",
  total_amount: "1700.00",
  customer_payable_amount: "1700.00",
  customer_visible_notes: "Found a worn belt during inspection.",
  rejection_reason: null,
  revision_reason: null,
  created_at: "2026-07-01T10:00:00Z",
};

describe("parseQuoteList", () => {
  it("parses a real multi-quote envelope", () => {
    const result = parseQuoteList([validQuote, { ...validQuote, id: "q2", status: "draft" }]);
    expect(result).toHaveLength(2);
    expect(result?.[0].id).toBe("q1");
  });

  it("drops individually-invalid entries rather than failing the whole list", () => {
    const result = parseQuoteList([validQuote, { id: "bad" }]);
    expect(result).toHaveLength(1);
  });

  it("fails safe on a malformed envelope", () => {
    expect(parseQuoteList({ not: "an array" })).toBeNull();
  });
});

describe("parseQuoteDetail", () => {
  it("parses a real quote-detail response with items", () => {
    const result = parseQuoteDetail({
      ...validQuote,
      items: [
        {
          id: "i1",
          item_type: "part",
          item_name: "Compressor belt",
          item_description: null,
          quantity: "1",
          unit_price: "1200.00",
          line_total: "1200.00",
          is_customer_visible: true,
        },
      ],
    });
    expect(result?.items).toHaveLength(1);
    expect(result?.items[0].item_name).toBe("Compressor belt");
  });

  it("filters out items not flagged is_customer_visible — server does not filter these itself (real, disclosed gap)", () => {
    const result = parseQuoteDetail({
      ...validQuote,
      items: [
        {
          id: "i1",
          item_type: "part",
          item_name: "Visible part",
          item_description: null,
          quantity: "1",
          unit_price: "100",
          line_total: "100",
          is_customer_visible: true,
        },
        {
          id: "i2",
          item_type: "labour",
          item_name: "Internal margin line",
          item_description: null,
          quantity: "1",
          unit_price: "50",
          line_total: "50",
          is_customer_visible: false,
        },
      ],
    });
    expect(result?.items).toHaveLength(1);
    expect(result?.items[0].id).toBe("i1");
  });

  it("structurally excludes provider_internal_notes and other internal-only fields even when the server includes them", () => {
    const result = parseQuoteDetail({
      ...validQuote,
      provider_internal_notes: "do not show this to the customer",
      idempotency_key: "some-key",
      locked_at: "2026-07-01T10:00:00Z",
      created_by_user_id: "staff-user-id",
      items: [],
    });
    expect(result).not.toHaveProperty("provider_internal_notes");
    expect(result).not.toHaveProperty("idempotency_key");
    expect(result).not.toHaveProperty("locked_at");
    expect(result).not.toHaveProperty("created_by_user_id");
  });

  it("drops individually-invalid items without failing the whole quote", () => {
    const result = parseQuoteDetail({ ...validQuote, items: [{ id: "bad-item" }] });
    expect(result?.items).toHaveLength(0);
  });

  it("fails safe on a malformed envelope", () => {
    expect(parseQuoteDetail({ status: "sent_to_customer" })).toBeNull();
  });
});

describe("toNumber", () => {
  it("passes through numbers and parses numeric strings", () => {
    expect(toNumber(42)).toBe(42);
    expect(toNumber("1700.00")).toBe(1700);
  });
});
