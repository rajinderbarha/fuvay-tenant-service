import React from "react";
import { View } from "react-native";
import { useTheme } from "../../design-system/theme";
import { AppText } from "../AppText";
import { AppCard } from "../AppCard";
import { CustomerBookingStage } from "../../domain/customerBookingDetails";
import { RECEIPT_TIMELINE_STEPS, resolveTimelineStepState } from "../../domain/bookingStatus";

/** Same four-step journey as the Confirmation Receipt's BookingTimeline,
 * wrapped in its own card per this screen's design (spec section 5:
 * "Booking journey"). Reuses `resolveTimelineStepState` rather than
 * re-deriving step logic. */
export function BookingJourney({ stage }: { stage: CustomerBookingStage }) {
  const { theme } = useTheme();
  return (
    <AppCard>
      <AppText variant="labelStrong" color="secondary">Booking journey</AppText>
      <View style={{ flexDirection: "row", marginTop: theme.spacing.sm }}>
        {RECEIPT_TIMELINE_STEPS.map((step, i) => {
          const state = resolveTimelineStepState(step.key, stage);
          const bg = state === "complete" ? theme.colors.statusSuccess : state === "active" ? theme.colors.brandPrimary : theme.colors.surfaceInteractive;
          const fg = state === "pending" ? theme.colors.textSecondary : theme.colors.brandOnPrimary;
          return (
            <View key={step.key} style={{ flex: 1, alignItems: "center" }}>
              <View style={{ width: 24, height: 24, borderRadius: theme.radius.radiusFull, backgroundColor: bg, alignItems: "center", justifyContent: "center" }}>
                <AppText variant="labelStrong" style={{ color: fg }}>{i + 1}</AppText>
              </View>
              <AppText variant="caption" align="center" style={{ marginTop: theme.spacing.xxs }}>{step.label}</AppText>
            </View>
          );
        })}
      </View>
    </AppCard>
  );
}
