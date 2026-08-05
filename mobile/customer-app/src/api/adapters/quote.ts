import { QuoteDto, quoteDtoSchema } from "../contracts/quotes";
import { Quote } from "../../domain/quote";
import { asQuoteId, asServiceJobId } from "../../domain/ids";
import { isQuoteStatus } from "../../domain/status";
import { parseServerTimestamp } from "../../domain/dates";
import { parseMoney } from "../../domain/money";
import { ContractValidationError, UnknownStatusError } from "../../domain/errors";

export function parseQuoteDto(raw: unknown): QuoteDto {
  const result = quoteDtoSchema.safeParse(raw);
  if (!result.success) {
    throw new ContractValidationError("QuoteDto", result.error.issues.map(i => i.message));
  }
  return result.data;
}

export function adaptQuote(dto: QuoteDto): Quote {
  if (!isQuoteStatus(dto.status)) {
    throw new UnknownStatusError("status", dto.status, dto.id);
  }
  const currency = dto.currency ?? "INR";
  return {
    id: asQuoteId(dto.id),
    jobId: asServiceJobId(dto.job_id),
    status: dto.status,
    amount: dto.amount != null ? parseMoney(dto.amount, currency) : null,
    visitFee: dto.visit_fee != null ? parseMoney(dto.visit_fee, currency) : null,
    notes: dto.notes ?? null,
    expiresAt: dto.expires_at ? parseServerTimestamp(dto.expires_at, "expires_at") : null,
    createdAt: dto.created_at ? parseServerTimestamp(dto.created_at, "created_at") : null,
  };
}
