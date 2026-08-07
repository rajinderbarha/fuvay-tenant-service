import React from "react";
import { View } from "react-native";
import { useTheme } from "../../design-system/theme";
import { AppText } from "../AppText";
import { AppCard } from "../AppCard";
import { AppBadge } from "../AppBadge";
import { Icon } from "../Icon";
import { ReceiptAddress } from "../../domain/bookingReceipt";

/** Read-only -- no edit action (spec: "Do not allow address editing after
 * confirmation from this receipt"). */
export function FinalizedAddressCard({ address }: { address: ReceiptAddress }) {
  const { theme } = useTheme();
  return (
    <AppCard>
      <AppText variant="labelStrong" color="secondary">Service address</AppText>
      <View style={{ flexDirection: "row", alignItems: "center", gap: theme.spacing.sm, marginTop: theme.spacing.xs }}>
        <View
          style={{
            width: 40, height: 40, borderRadius: theme.radius.radiusFull,
            backgroundColor: "#7C3AED", alignItems: "center", justifyContent: "center", flexShrink: 0,
          }}
        >
          <Icon name={address.label?.toLowerCase() === "home" ? "home" : "location"} size="standard" color="#FFFFFF" decorative />
        </View>
        <View style={{ flex: 1, minWidth: 0 }}>
          {address.label ? <AppText variant="body">{address.label}</AppText> : null}
          <AppText variant="bodySmall" color="secondary">{address.formatted}</AppText>
        </View>
        <AppBadge label="Serviceable" tone="success" />
      </View>
    </AppCard>
  );
}
