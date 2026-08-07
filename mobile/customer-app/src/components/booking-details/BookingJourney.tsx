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

/**
 * Fixed per-step colour and glyph, taken from the design (node 5944-302):
 * indigo check, green assignment, violet schedule.
 *
 * IMPORTANT -- these are NOT progress colours. The reference shows all
 * three steps fully coloured regardless of where the booking actually is,
 * so this row reads as a map of the three stages, not an indicator of
 * which one has been reached. Implemented that way on explicit request
 * ("100% same design"); `resolveTimelineStepState` is still used below,
 * but only for the accessible label, so a screen reader can still say
 * which step is current even though the visuals do not distinguish it.
 */
const STEP_STYLE: ReadonlyArray<{ color: string; icon: IconProps["name"] }> = [
  { color: "#3730A3", icon: "checkmark-circle-outline" },
  { color: "#047857", icon: "briefcase-outline" },
  { color: "#7C3AED", icon: "calendar-outline" },
];

export function BookingJourney({ stage, bare = false }: BookingJourneyProps) {
  const { theme } = useTheme();
  const content = (
    <>
      <AppText variant="bodyStrong">Booking journey</AppText>
      <View
        style={{
          marginTop: theme.spacing.xs,
          paddingVertical: theme.spacing.sm,
          paddingHorizontal: theme.spacing.base,
          borderRadius: theme.radiusUsage.card,
          borderWidth: 1,
          borderColor: theme.colors.borderSubtle,
          backgroundColor: theme.colors.surfaceSecondary,
          flexDirection: "row",
          alignItems: "flex-start",
        }}
      >
        {RECEIPT_TIMELINE_STEPS.map((step, i) => {
          const state = resolveTimelineStepState(step.key, stage);
          const isLast = i === RECEIPT_TIMELINE_STEPS.length - 1;
          return (
            <React.Fragment key={step.key}>
              <View
                style={{ alignItems: "center", width: 72 }}
                accessible
                accessibilityLabel={`${step.label}${state === "active" ? ", current step" : state === "complete" ? ", done" : ""}`}
              >
                <View
                  style={{
                    width: 34, height: 34, borderRadius: theme.radius.radiusFull,
                    backgroundColor: STEP_STYLE[i].color,
                    alignItems: "center", justifyContent: "center",
                  }}
                >
                  <Icon name={STEP_STYLE[i].icon} size="compact" color="#FFFFFF" decorative />
                </View>
                <AppText variant="caption" color="secondary" align="center" style={{ marginTop: theme.spacing.xs }}>
                  {step.label}
                </AppText>
              </View>
              {!isLast ? (
                // Dotted connector, aligned to the circles' vertical centre.
                <View
                  style={{
                    flex: 1, marginTop: 17,
                    borderTopWidth: 2, borderStyle: "dotted",
                    borderColor: theme.colors.borderDefault,
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
