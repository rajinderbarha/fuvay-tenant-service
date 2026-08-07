import React from "react";
import { View } from "react-native";
import { useTheme } from "../../design-system/theme";
import { AppText } from "../AppText";
import { AppCard } from "../AppCard";
import { CustomerBookingStage } from "../../domain/customerBookingDetails";
import { resolveTimelineStepState, TimelineStepState } from "../../domain/bookingStatus";

/**
 * Numbered-circle journey stepper for the request-confirmed state of
 * Booking Details, matching the design's own visual language for this
 * screen -- distinct from `BookingJourney`'s colour-coded icon circles
 * used on My Bookings/Home, a separate, already-confirmed design for that
 * surface. Kept as its own component so neither design can drift the
 * other.
 *
 * Three visual states, all showing the step NUMBER (never a checkmark
 * glyph, per the real design): done = solid success-green, current =
 * solid brand colour, not yet reached = grey outline. Colours are the
 * app's own existing tokens (statusSuccess/brandPrimary), not new ones
 * introduced for this screen.
 *
 * A 4th step, "Service visit", is shown for completeness with the design
 * but is NEVER marked done or current here: this component only renders
 * while the booking is still in its earliest state (see
 * BookingDetailsScreen, the only caller -- once a job reaches
 * assignment/scheduled/on_the_way the screen switches to
 * `JobProgressTimeline`, which owns that later evidence). Rendering it
 * any other way would claim a visit is underway without the backend
 * having said so.
 */
export function RequestJourneyStepper({ stage }: { stage: CustomerBookingStage }) {
  const { theme } = useTheme();

  const steps = [
    { key: "request_confirmed" as const, label: "Request confirmed" },
    { key: "provider_assignment" as const, label: "Provider assignment" },
    { key: "scheduled" as const, label: "Visit scheduling" },
    { key: "service_visit" as const, label: "Service visit" },
  ];

  function stateFor(key: (typeof steps)[number]["key"]): TimelineStepState {
    return key === "service_visit" ? "pending" : resolveTimelineStepState(key, stage);
  }

  // Index of the furthest step this stage has genuinely reached, among
  // the three real ones -- "Service visit" can never contribute here.
  const reachedIndex = steps.reduce((acc, step, i) => (stateFor(step.key) !== "pending" ? i : acc), 0);
  const progressPercent = (reachedIndex / (steps.length - 1)) * 100;

  return (
    <View>
      {/* Overall progress, outside any card per the design -- a plain
          fraction of steps reached, not a time-based estimate. The small
          circular knob marks the fill boundary, matching the design's
          slider-like bar. */}
      <View
        style={{ height: 4, justifyContent: "center", marginBottom: theme.spacing.base }}
        accessibilityRole="progressbar"
        accessibilityLabel={`Booking progress: step ${reachedIndex + 1} of ${steps.length}`}
      >
        <View style={{ height: 4, borderRadius: theme.radius.radiusFull, backgroundColor: theme.colors.borderSubtle, overflow: "hidden" }}>
          <View style={{ width: `${progressPercent}%`, height: "100%", backgroundColor: theme.colors.brandPrimary }} />
        </View>
        <View
          style={{
            position: "absolute", left: `${progressPercent}%`, marginLeft: -6,
            width: 12, height: 12, borderRadius: theme.radius.radiusFull,
            backgroundColor: theme.colors.brandPrimary,
            borderWidth: 2, borderColor: theme.colors.surfaceDefault,
          }}
        />
      </View>

      <AppCard>
        <AppText variant="labelStrong" color="secondary">Booking journey</AppText>
        <View style={{ flexDirection: "row", alignItems: "flex-start", marginTop: theme.spacing.sm }}>
          {steps.map((step, i) => {
            const state = stateFor(step.key);
            const isLast = i === steps.length - 1;
            const circleColor = state === "complete" ? theme.colors.statusSuccess
              : state === "active" ? theme.colors.brandPrimary
              : null;
            return (
              <React.Fragment key={step.key}>
                <View
                  style={{ alignItems: "center", width: 68 }}
                  accessible
                  accessibilityLabel={`${step.label}${state === "complete" ? ", done" : state === "active" ? ", current step" : ", not yet reached"}`}
                >
                  <View
                    style={{
                      width: 36, height: 36, borderRadius: theme.radius.radiusFull,
                      alignItems: "center", justifyContent: "center",
                      backgroundColor: circleColor ?? theme.colors.surfaceSecondary,
                      borderWidth: circleColor ? 0 : 1, borderColor: theme.colors.borderDefault,
                    }}
                  >
                    <AppText variant="labelStrong" style={{ color: circleColor ? theme.colors.brandOnPrimary : theme.colors.textTertiary }}>
                      {String(i + 1).padStart(2, "0")}
                    </AppText>
                  </View>
                  <AppText
                    variant="caption"
                    color={state === "pending" ? "tertiary" : "secondary"}
                    align="center"
                    style={{ marginTop: theme.spacing.xs }}
                  >
                    {step.label}
                  </AppText>
                </View>
                {!isLast ? (
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
      </AppCard>
    </View>
  );
}
