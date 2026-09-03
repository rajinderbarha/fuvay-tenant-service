import React from "react";
import { View } from "react-native";
import { useTheme } from "../../design-system/theme";
import { AppButton } from "../AppButton";

export interface BookingDetailsActionsProps {
  onRefresh: () => void;
  refreshing: boolean;
  onContactSupport?: () => void;
}

export function BookingDetailsActions({ onRefresh, refreshing, onContactSupport }: BookingDetailsActionsProps) {
  const { theme } = useTheme();
  const pill = { borderRadius: theme.radius.radiusFull };
  return (
    <View style={{ gap: theme.spacing.sm }}>
      <AppButton label="Refresh status" onPress={onRefresh} loading={refreshing} fullWidth style={pill} />
      {onContactSupport ? (
        <AppButton label="Contact support" tone="secondary" onPress={onContactSupport} fullWidth style={pill} />
      ) : null}
    </View>
  );
}
