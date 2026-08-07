import React from "react";
import { View } from "react-native";
import { useTheme } from "../../design-system/theme";
import { AppText } from "../AppText";
import { AppCard } from "../AppCard";
import { Icon, IconProps } from "../Icon";
import { CustomerBookingStage } from "../../domain/customerBookingDetails";
import { RECEIPT_TIMELINE_STEPS, resolveTimelineStepState } from "../../domain/bookingStatus";

export interface BookingJourneyProps {
  stage: CustomerBookingStage;
  /** Skip the surrounding AppCard when the caller already provides one --
   * My Bookings' active card was rendering a card inside a card before
   * this prop existed. Booking Details renders this section standalone,
   * so it keeps the default (wrapped). */
  bare?: boolean;
}

const STEP_ICONS: ReadonlyArray<IconProps["name"]> = [
  "checkmark-outline", "people-outline", "calendar-outline",
];

/**
 * Same three-step journey as the Confirmation Receipt's BookingTimeline.
 * Reuses `resolveTimelineStepState` rather than re-deriving step logic --
 * a step is only ever coloured "complete" on backend evidence for that
 * stage, never inferred from elapsed time (see bookingStatus.ts). The
 * Figma reference shows all three steps solid-coloured regardless of
 * progress; that was NOT copied here, since it would contradict that
 * evidence rule -- a step still ahead of the real status stays visually
 * pending (grey), not fabricated as reached.
 */
export function BookingJourney({ stage, bare = false }: BookingJourneyProps) {
  const { theme } = useTheme();
  const content = (
    <>
      <AppText variant="labelStrong" color="secondary">Booking journey</AppText>
      <View style={{ flexDirection: "row", marginTop: theme.spacing.sm }}>
        {RECEIPT_TIMELINE_STEPS.map((step, i) => {
          const state = resolveTimelineStepState(step.key, stage);
          const bg = state === "complete" ? theme.colors.statusSuccess : state === "active" ? theme.colors.brandPrimary : theme.colors.surfaceInteractive;
          const fg = state === "pending" ? theme.colors.textSecondary : theme.colors.brandOnPrimary;
          const isLast = i === RECEIPT_TIMELINE_STEPS.length - 1;
          return (
            <React.Fragment key={step.key}>
              <View style={{ alignItems: "center", width: 64 }}>
                <View style={{ width: 28, height: 28, borderRadius: theme.radius.radiusFull, backgroundColor: bg, alignItems: "center", justifyContent: "center" }}>
                  <Icon name={STEP_ICONS[i]} size="compact" color={fg} decorative />
                </View>
                <AppText variant="caption" align="center" style={{ marginTop: theme.spacing.xxs }}>{step.label}</AppText>
              </View>
              {!isLast ? (
                <View
                  style={{
                    flex: 1, height: 1, marginTop: 14,
                    borderStyle: "dashed", borderWidth: 1, borderColor: theme.colors.borderDefault,
                  }}
                />
              ) : null}
            </React.Fragment>
          );
        })}
      </View>
    </>
  );
  return bare ? content : <AppCard>{content}</AppCard>;
}
