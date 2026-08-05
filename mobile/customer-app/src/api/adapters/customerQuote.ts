import { CustomerQuoteDto } from "../contracts/customerQuote";
import { CustomerQuote } from "../../domain/customerQuote";

export function adaptCustomerQuote(dto: CustomerQuoteDto): CustomerQuote {
  return {
    id: dto.id,
    quoteNumber: dto.quote_number,
    jobId: dto.job_id,
    rawStatus: dto.status,
    currency: dto.currency,
    totalAmount: dto.total_amount,
    customerPayableAmount: dto.customer_payable_amount,
    findingSummary: dto.customer_visible_notes,
    rejectionReason: dto.rejection_reason,
    isCurrent: dto.is_current,
    items: (dto.items ?? []).map(i => ({
      id: i.id,
      label: i.item_name,
      description: i.item_description,
      quantity: i.quantity,
      unitAmount: i.unit_price,
      lineTotal: i.line_total,
    })),
  };
}
