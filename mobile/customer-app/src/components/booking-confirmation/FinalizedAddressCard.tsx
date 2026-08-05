import React from "react";
import { View } from "react-native";
import { useTheme } from "../../design-system/theme";
import { AppText } from "../AppText";
import { AppCard } from "../AppCard";
import { AppBadge } from "../AppBadge";
import { ReceiptAddress } from "../../domain/bookingReceipt";

/** Read-only -- no edit action (spec: "Do not allow address editing after
 * confirmation from this receipt"). */
export function FinalizedAddressCard({ address }: { address: ReceiptAddress }) {
  const { theme } = useTheme();
  return (
    <AppCard>
      <View style={{ flexDirection: "row", justifyContent: "space-between", alignItems: "center" }}>
        <AppText variant="labelStrong" color="secondary">Service address</AppText>
        <AppBadge label="Serviceable" tone="success" />
      </View>
      <View style={{ marginTop: theme.spacing.xxs }}>
        {address.label ? <AppText variant="body">{address.label}</AppText> : null}
        <AppText variant="bodySmall" color="secondary">{address.formatted}</AppText>
      </View>
    </AppCard>
  );
}
