import { PartsRequestListDto } from "../contracts/customerParts";
import { CustomerPartsRequestList } from "../../domain/customerParts";

export function adaptCustomerPartsRequestList(dto: PartsRequestListDto): CustomerPartsRequestList {
  return {
    currency: dto.currency,
    previousEstimatedTotal: dto.previous_estimated_total,
    additionalTotal: dto.additional_total,
    newEstimatedTotal: dto.new_estimated_total,
    items: dto.items.map(i => ({
      id: i.parts_request_id,
      rawStatus: i.status,
      partName: i.part_name,
      quantity: i.quantity,
      unitAmount: i.unit_amount,
      lineTotal: i.line_total,
      reason: i.reason,
      customerApprovalRequired: i.customer_approval_required,
      submittedAt: i.submitted_at,
      decidedAt: i.decided_at,
      rejectionReason: i.rejection_reason,
    })),
  };
}
