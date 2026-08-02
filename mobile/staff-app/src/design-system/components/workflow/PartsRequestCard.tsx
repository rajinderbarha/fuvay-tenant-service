import React from "react";
import { View } from "react-native";
import { useTheme } from "../../themes";
import { AppText } from "../typography/AppText";
import { Card } from "../foundation/Layout";

export type PartsRequestStatus =
  | "draft" | "submitted" | "business_approved" | "business_rejected"
  | "customer_approval_pending" | "customer_approved" | "customer_rejected" | "installed" | "cancelled";

const STATUS_LABEL: Record<PartsRequestStatus, string> = {
  draft: "Draft", submitted: "Submitted", business_approved: "Approved", business_rejected: "Rejected",
  customer_approval_pending: "Awaiting customer approval", customer_approved: "Customer approved",
  customer_rejected: "Customer rejected", installed: "Installed", cancelled: "Cancelled",
};

export interface PartsRequestCardProps {
  partName: string;
  quantity: number;
  status: PartsRequestStatus;
  reason?: string;
}

/** Technician cannot approve their own request -- this component never
 * renders an approve/reject action, only status. */
export function PartsRequestCard({ partName, quantity, status, reason }: PartsRequestCardProps) {
  const { theme } = useTheme();
  const isRejected = status === "business_rejected" || status === "customer_rejected" || status === "cancelled";
  const isApproved = status === "business_approved" || status === "customer_approved" || status === "installed";

  return (
    <Card>
      <View style={{ flexDirection: "row", justifyContent: "space-between" }}>
        <AppText variant="bodyStrong">{partName} × {quantity}</AppText>
        <AppText variant="bodySmall" color={isRejected ? "danger" : isApproved ? "success" : "secondary"}>
          {STATUS_LABEL[status]}
        </AppText>
      </View>
      {reason ? <AppText variant="caption" color="tertiary" style={{ marginTop: 4 }}>{reason}</AppText> : null}
    </Card>
  );
}
