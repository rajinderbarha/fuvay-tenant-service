import { parseQuoteDto, adaptQuote } from "../adapters/quote";
import { makeQuoteDto } from "../../testing/fixtures";
import { UnknownStatusError } from "../../domain/errors";

describe("Quote adapter", () => {
  it("adapts amount and visit_fee into Money without float error", () => {
    const dto = parseQuoteDto(makeQuoteDto());
    const quote = adaptQuote(dto);
    expect(quote.amount).toEqual({ minorUnits: 149900, currency: "INR" });
    expect(quote.visitFee).toEqual({ minorUnits: 19900, currency: "INR" });
  });

  it("handles a null amount", () => {
    const dto = parseQuoteDto(makeQuoteDto({ amount: null }));
    const quote = adaptQuote(dto);
    expect(quote.amount).toBeNull();
  });

  it("rejects an unknown quote status", () => {
    const dto = parseQuoteDto(makeQuoteDto({ status: "haggling" }));
    expect(() => adaptQuote(dto)).toThrow(UnknownStatusError);
  });
});
