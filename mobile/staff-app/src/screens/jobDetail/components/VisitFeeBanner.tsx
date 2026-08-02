import React from "react";
import { InlineAlert } from "../../../design-system/components/feedback/Banner";
import { VisitFeeDTO } from "../../../services/jobDetail/types";

/** Renders only the backend-provided visit-fee policy -- never a hardcoded
 * amount (spec section 14). Nothing rendered when unavailable/not required. */
export function VisitFeeBanner({ visitFee }: { visitFee: VisitFeeDTO }) {
  if (!visitFee.required || visitFee.amount === null) return null;
  const amountLabel = `₹${visitFee.amount.toLocaleString("en-IN")}`;
  return (
    <InlineAlert
      tone="info"
      title={`Visit fee ${amountLabel}`}
      message={visitFee.policy_note ?? "Adjusted if work continues."}
    />
  );
}
