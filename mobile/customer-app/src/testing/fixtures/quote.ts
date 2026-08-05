import { QuoteDto } from "../../api/contracts/quotes";

export function makeQuoteDto(overrides: Partial<QuoteDto> = {}): QuoteDto {
  return {
    id: "quote-aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa",
    job_id: "job-11111111-1111-1111-1111-111111111111",
    status: "sent",
    amount: "1499.00",
    currency: "INR",
    visit_fee: "199.00",
    notes: "Replacement part required.",
    expires_at: "2026-08-10T00:00:00Z",
    created_at: "2026-08-02T12:00:00Z",
    ...overrides,
  };
}
