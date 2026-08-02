import React from "react";
import { View } from "react-native";
import { useTheme } from "../../../design-system/themes";
import { AppText } from "../../../design-system/components/typography/AppText";
import { PartUsedDTO } from "../../../services/completionProof/types";

const LABEL: Record<string, string> = {
  requested: "Tenant approval", business_approved: "Approved", customer_approval_pending: "Customer approval",
  customer_approved: "Approved", business_rejected: "Rejected", customer_rejected: "Rejected",
  installed: "Recorded", cancelled: "Cancelled",
};

/** Read-only reconciliation of approved parts -- no cost editing here
 * (spec section 9). "Recorded" mirrors the reference design's wording for
 * an installed part; approved-but-not-yet-installed parts show "Approved". */
export function PartsUsedList({ parts }: { parts: PartUsedDTO[] }) {
  const { theme } = useTheme();
  if (parts.length === 0) {
    return <AppText variant="bodySmall" color="tertiary">No parts used.</AppText>;
  }
  return (
    <View>
      {parts.map(part => (
        <View key={part.parts_request_id} style={{ flexDirection: "row", justifyContent: "space-between", paddingVertical: theme.spacing.sm, borderBottomWidth: 1, borderBottomColor: theme.colors.borderSubtle }}>
          <AppText variant="body">{part.part_name} · Qty {part.quantity}</AppText>
          <AppText variant="caption" color={part.status.includes("rejected") ? "danger" : "tertiary"}>{LABEL[part.status] ?? part.status}</AppText>
        </View>
      ))}
    </View>
  );
}
