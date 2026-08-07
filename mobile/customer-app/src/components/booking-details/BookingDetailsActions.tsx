import React from "react";
import { View } from "react-native";
import { useTheme } from "../../design-system/theme";
import { AppText } from "../AppText";
import { AppButton } from "../AppButton";

export interface BookingDetailsActionsProps {
  onRefresh: () => void;
  refreshing: boolean;
  onContactSupport?: () => void;
}

/** No Cancel/Reschedule buttons -- both are confirmed-disconnected
 * capabilities this phase (spec section 7); the informational line below
 * is the only acknowledgement, never a disabled dead button. */
export function BookingDetailsActions({ onRefresh, refreshing, onContactSupport }: BookingDetailsActionsProps) {
  const { theme } = useTheme();
  const pill = { borderRadius: theme.radius.radiusFull };
  return (
    <View style={{ gap: theme.spacing.sm }}>
      <AppButton label="Refresh status" onPress={onRefresh} loading={refreshing} fullWidth style={pill} />
      {onContactSupport ? (
        <AppButton label="Contact support" tone="secondary" onPress={onContactSupport} fullWidth style={pill} />
      ) : null}
      <AppText variant="caption" color="tertiary" align="center">
        Cancellation and rescheduling are not available in the app yet.
      </AppText>
    </View>
  );
}
