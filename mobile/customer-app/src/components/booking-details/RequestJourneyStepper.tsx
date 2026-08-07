import React from "react";
import { View } from "react-native";
import { useTheme } from "../../design-system/theme";
import { AppText } from "../AppText";
import { AppCard } from "../AppCard";
import { Icon } from "../Icon";
import { CustomerBookingStage } from "../../domain/customerBookingDetails";
import { resolveTimelineStepState } from "../../domain/bookingStatus";

/**
 * Numbered-circle journey stepper for the request-confirmed state of
 * Booking Details, matching the design's own visual language for this
 * screen (plain numbered circles + a thin overall progress bar) --
 * distinct from `BookingJourney`'s colour-coded icon circles used on My
 * Bookings/Home, which is a separate, already-confirmed design for that
 * surface. Kept as its own component rather than a shared one so neither
 * design can accidentally drift the other.
 *
 * A 4th step, "Service visit", is shown for completeness with the design
 * but is NEVER marked reached here: this component only renders while the
 * booking is still in its earliest state (see BookingDetailsScreen, the
 * only caller -- once a job reaches assignment/scheduled/on_the_way the
 * screen switches to `JobProgressTimeline`, which owns that later
 * evidence). Rendering it any other way would claim a visit is underway
 * without the backend having said so.
 */
export function RequestJourneyStepper({ stage }: { stage: CustomerBookingStage }) {
  const { theme } = useTheme();

  const steps = [
    { key: "request_confirmed" as const, label: "Request confirmed" },
    { key: "provider_assignment" as const, label: "Provider assignment" },
    { key: "scheduled" as const, label: "Visit scheduling" },
    { key: "service_visit" as const, label: "Service visit" },
  ];

  // Index of the furthest step this stage has genuinely reached, among
  // the three real ones -- "Service visit" can never contribute here.
  const reachedIndex = steps.reduce((acc, step, i) => {
    if (step.key === "service_visit") return acc;
    const state = resolveTimelineStepState(step.key, stage);
    return state !== "pending" ? i : acc;
  }, 0);
  const progressPercent = (reachedIndex / (steps.length - 1)) * 100;

  return (
    <View>
      {/* Overall progress, outside any card per the design -- a plain
          fraction of steps reached, not a time-based estimate. */}
      <View
        style={{ height: 4, borderRadius: theme.radius.radiusFull, backgroundColor: theme.colors.borderSubtle, overflow: "hidden", marginBottom: theme.spacing.base }}
        accessibilityRole="progressbar"
        accessibilityLabel={`Booking progress: step ${reachedIndex + 1} of ${steps.length}`}
      >
        <View style={{ width: `${progressPercent}%`, height: "100%", backgroundColor: theme.colors.brandPrimary }} />
      </View>

      <AppText variant="headingSmall">Booking journey</AppText>

      <AppCard style={{ marginTop: theme.spacing.sm }}>
        <View style={{ flexDirection: "row", alignItems: "flex-start" }}>
          {steps.map((step, i) => {
            const reached = step.key !== "service_visit" && resolveTimelineStepState(step.key, stage) !== "pending";
            const isLast = i === steps.length - 1;
            return (
              <React.Fragment key={step.key}>
                <View
                  style={{ alignItems: "center", width: 68 }}
                  accessible
                  accessibilityLabel={`${step.label}${reached ? ", done" : ", not yet reached"}`}
                >
                  <View
                    style={{
                      width: 36, height: 36, borderRadius: theme.radius.radiusFull,
                      alignItems: "center", justifyContent: "center",
                      backgroundColor: reached ? theme.colors.brandPrimary : theme.colors.surfaceSecondary,
                      borderWidth: reached ? 0 : 1, borderColor: theme.colors.borderDefault,
                    }}
                  >
                    {reached ? (
                      <Icon name="checkmark" size="compact" color={theme.colors.brandOnPrimary} decorative />
                    ) : (
                      <AppText variant="labelStrong" color="tertiary">{String(i + 1).padStart(2, "0")}</AppText>
                    )}
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
