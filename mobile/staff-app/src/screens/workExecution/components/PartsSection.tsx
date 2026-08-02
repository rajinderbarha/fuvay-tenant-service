import React from "react";
import { View } from "react-native";
import { useTheme } from "../../../design-system/themes";
import { AppText } from "../../../design-system/components/typography/AppText";
import { Icon } from "../../../design-system/components/Icon";
import { PartsRequestDTO } from "../../../services/workExecution/types";

const STATUS_LABEL: Record<string, string> = {
  requested: "Tenant approval", business_approved: "Approved", customer_approval_pending: "Customer approval",
  customer_approved: "Approved", business_rejected: "Rejected", customer_rejected: "Rejected",
  installed: "Installed", cancelled: "Cancelled",
};

function statusColor(theme: ReturnType<typeof useTheme>["theme"], status: string): string {
  if (status === "installed" || status === "business_approved" || status === "customer_approved") return theme.colors.statusSuccess;
  if (status === "business_rejected" || status === "customer_rejected" || status === "cancelled") return theme.colors.statusDanger;
  return theme.colors.statusWarning;
}

/** Every part shown here is an approved-estimate or pending-request record
 * from the canonical PartsRequest model -- marking a part "installed" never
 * changes its approved amount (spec section 9). */
export function PartsSection({ parts }: { parts: PartsRequestDTO[] }) {
  const { theme } = useTheme();
  if (parts.length === 0) {
    return <AppText variant="bodySmall" color="tertiary">No parts requested yet.</AppText>;
  }
  return (
    <View>
      {parts.map(part => (
        <View key={part.parts_request_id} style={{ flexDirection: "row", alignItems: "center", paddingVertical: theme.spacing.sm, gap: theme.spacing.sm, borderBottomWidth: 1, borderBottomColor: theme.colors.borderSubtle }}>
          {(part.status === "installed" || part.status.includes("approved")) ? (
            <Icon name="checkmark-circle" size="compact" color={theme.colors.statusSuccess} decorative />
          ) : (part.status.includes("rejected") || part.status === "cancelled") ? (
            <Icon name="close-circle" size="compact" color={theme.colors.statusDanger} decorative />
          ) : (
            <Icon name="time-outline" size="compact" color={theme.colors.statusWarning} decorative />
          )}
          <View style={{ flex: 1 }}>
            <AppText variant="body">{part.part_name} · Qty {part.quantity}</AppText>
            {part.status.includes("rejected") && part.rejection_reason ? (
              <AppText variant="caption" color="danger">{part.rejection_reason}</AppText>
            ) : null}
          </View>
          <AppText variant="caption" style={{ color: statusColor(theme, part.status) }}>{STATUS_LABEL[part.status] ?? part.status}</AppText>
        </View>
      ))}
    </View>
  );
}
