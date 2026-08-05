export interface CustomerPartsRequestItem {
  id: string;
  rawStatus: string;
  partName: string;
  quantity: number;
  unitAmount: string;
  lineTotal: string;
  reason: string;
  customerApprovalRequired: boolean;
  submittedAt: string | null;
  decidedAt: string | null;
  rejectionReason: string | null;
}

/** All monetary totals are backend-computed -- this app never sums,
 * discounts, or otherwise derives `additionalTotal`/`newEstimatedTotal`
 * itself (see `_customer_safe_job`'s sibling `customer_list_parts_requests`
 * in `home_service_service.py`). */
export interface CustomerPartsRequestList {
  currency: string;
  previousEstimatedTotal: string;
  additionalTotal: string;
  newEstimatedTotal: string;
  items: CustomerPartsRequestItem[];
}
