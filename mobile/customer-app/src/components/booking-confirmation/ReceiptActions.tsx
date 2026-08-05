import React from "react";
import { View } from "react-native";
import { useTheme } from "../../design-system/theme";
import { AppButton } from "../AppButton";

export interface ReceiptActionsProps {
  onViewBooking: () => void;
  onBackToHome: () => void;
  onContactSupport?: () => void;
}

/** `onContactSupport` omitted entirely (not just disabled) hides the
 * action -- spec: "If no support destination exists, hide the action
 * rather than creating a dead button." */
export function ReceiptActions({ onViewBooking, onBackToHome, onContactSupport }: ReceiptActionsProps) {
  const { theme } = useTheme();
  return (
    <View style={{ gap: theme.spacing.sm }}>
      {onContactSupport ? (
        <AppButton label="Contact support" tone="tertiary" onPress={onContactSupport} fullWidth />
      ) : null}
      <AppButton label="View booking" onPress={onViewBooking} fullWidth />
      <AppButton label="Back to home" tone="secondary" onPress={onBackToHome} fullWidth />
    </View>
  );
}
