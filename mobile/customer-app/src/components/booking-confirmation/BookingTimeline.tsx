import React from "react";
import { View } from "react-native";
import { useTheme } from "../../design-system/theme";
import { AppText } from "../AppText";
import { BookingReceiptStage, RECEIPT_TIMELINE_STEPS, resolveTimelineStepState } from "../../domain/bookingStatus";

export interface BookingTimelineProps {
  currentStage: BookingReceiptStage;
}

/** Three fixed steps, states derived purely from `currentStage` -- never a
 * timer (spec section 4: "Never use timers to advance the timeline"). */
export function BookingTimeline({ currentStage }: BookingTimelineProps) {
  const { theme } = useTheme();
  return (
    <View
      style={{ flexDirection: "row" }}
      accessibilityRole="progressbar"
      accessibilityLabel={`Booking progress: ${currentStage.replace(/_/g, " ")}`}
    >
      {RECEIPT_TIMELINE_STEPS.map((step, i) => {
        const state = resolveTimelineStepState(step.key, currentStage);
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
  );
}
