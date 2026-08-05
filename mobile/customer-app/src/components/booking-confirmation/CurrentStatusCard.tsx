import React from "react";
import { View } from "react-native";
import { useTheme } from "../../design-system/theme";
import { AppText } from "../AppText";
import { AppCard } from "../AppCard";
import { AppBadge } from "../AppBadge";

export interface CurrentStatusCardProps {
  statusLabel: string;
  activityText: string | null;
  supportingText: string | null;
}

/** Renders only truthful, backend-derived text -- `statusLabel` is
 * already a customer-safe mapped value (domain/bookingStatus.ts), never a
 * raw workflow enum. */
export function CurrentStatusCard({ statusLabel, activityText, supportingText }: CurrentStatusCardProps) {
  const { theme } = useTheme();
  return (
    <AppCard>
      <AppText variant="labelStrong" color="secondary">What's happening now</AppText>
      <View style={{ flexDirection: "row", alignItems: "center", justifyContent: "space-between", marginTop: theme.spacing.xxs }}>
        <View style={{ flexDirection: "row", alignItems: "center", gap: theme.spacing.xs, flex: 1 }}>
          <View style={{ width: 8, height: 8, borderRadius: theme.radius.radiusFull, backgroundColor: theme.colors.brandPrimary }} />
          <AppText variant="bodyStrong">{activityText ?? statusLabel}</AppText>
        </View>
        <AppBadge label="Request confirmed" tone="success" />
      </View>
      {supportingText ? (
        <AppText variant="bodySmall" color="secondary" style={{ marginTop: theme.spacing.xxs }}>{supportingText}</AppText>
      ) : null}
    </AppCard>
  );
}
