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
 * Per-step colour and glyph from the design (node 5944-302): indigo
 * check, green assignment, violet schedule.
 *
 * A step only wears its colour once the booking has actually REACHED it.
 * The reference frame shows all three filled, but it depicts a single
 * moment rather than a rule -- rendering it literally would paint
 * "Schedule" violet on a booking with no visit scheduled, which is the
 * one thing this row exists to tell the customer. Steps still ahead stay
 * muted, consistent with bookingStatus.ts's standing rule that a stage is
 * never shown as reached without backend evidence.
 */
/** Stage colours come from the Fuvay v2 accent rotation rather than fixed
 *  hexes: v2 ships a separate, darker set for light mode, so hardcoded
 *  values would be the wrong shade in one theme. Icons stay fixed. */
const STEP_ICONS: ReadonlyArray<IconProps["name"]> = [
  "checkmark-circle-outline",
  "briefcase-outline",
  "calendar-outline",
];

function stepColors(theme: ReturnType<typeof useTheme>["theme"]): string[] {
  return [theme.colors.accentCyan, theme.colors.accentMint, theme.colors.accentViolet];
}

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
          const reached = state === "complete" || state === "active";
          const isLast = i === RECEIPT_TIMELINE_STEPS.length - 1;
          return (
            <React.Fragment key={step.key}>
              <View
                style={{ alignItems: "center", width: 72 }}
                accessible
                accessibilityLabel={`${step.label}${state === "active" ? ", current step" : state === "complete" ? ", done" : ", not yet reached"}`}
              >
                <View
                  style={{
                    width: 34, height: 34, borderRadius: theme.radius.radiusFull,
                    backgroundColor: reached ? stepColors(theme)[i] : theme.colors.surfaceInteractive,
                    alignItems: "center", justifyContent: "center",
                  }}
                >
                  <Icon
                    name={STEP_ICONS[i]}
                    size="compact"
                    color={reached ? "#FFFFFF" : theme.colors.textTertiary}
                    decorative
                  />
                </View>
                <AppText
                  variant="caption"
                  color={reached ? "secondary" : "tertiary"}
                  align="center"
                  style={{ marginTop: theme.spacing.xs }}
                >
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
