import React from "react";
import { View } from "react-native";
import { useTheme } from "../../design-system/theme";
import { AppText } from "../AppText";
import { AppCard } from "../AppCard";
import { Icon } from "../Icon";
import { ActiveJobStage, JOB_PROGRESS_STEPS, resolveJobProgressStepState } from "../../domain/activeJobPresentation";

/** Mission's 5-step vertical "Job progress" timeline (Booked, Assigned,
 * Scheduled, On the way, Arrived). Only rendered once a real job has
 * reached one of the three stages this phase owns -- `activeStage` is
 * never derived from time or guesswork, only from `resolveActiveJobStage`.
 * A non-color status signal (check / dot / empty ring) accompanies every
 * step so status is never conveyed by color alone. */
export function JobProgressTimeline({ activeStage }: { activeStage: ActiveJobStage | "arrived" }) {
  const { theme } = useTheme();
  return (
    <AppCard>
      <AppText variant="labelStrong" color="secondary">Job progress</AppText>
      <View
        style={{ marginTop: theme.spacing.sm }}
        accessible
        accessibilityRole="progressbar"
        accessibilityLabel="Job progress"
      >
        {JOB_PROGRESS_STEPS.map((step, i) => {
          const state = resolveJobProgressStepState(step.key, activeStage);
          const isLast = i === JOB_PROGRESS_STEPS.length - 1;
          const dotColor = state === "complete" ? theme.colors.statusSuccess
            : state === "active" ? theme.colors.brandPrimary
            : theme.colors.borderSubtle;
          return (
            <View key={step.key} style={{ flexDirection: "row", gap: theme.spacing.sm }}>
              <View style={{ alignItems: "center" }}>
                <View
                  style={{
                    width: 24, height: 24, borderRadius: theme.radius.radiusFull, alignItems: "center", justifyContent: "center",
                    backgroundColor: state === "pending" ? "transparent" : dotColor,
                    borderWidth: state === "active" ? 2 : state === "pending" ? 1 : 0,
                    borderColor: state === "active" ? theme.colors.brandPrimary : theme.colors.borderSubtle,
                  }}
                >
                  {state === "complete" ? (
                    <Icon name="checkmark" size="compact" color={theme.colors.brandOnPrimary} decorative />
                  ) : state === "active" ? (
                    <View style={{ width: 8, height: 8, borderRadius: theme.radius.radiusFull, backgroundColor: theme.colors.brandPrimary }} />
                  ) : null}
                </View>
                {!isLast ? <View style={{ width: 2, flex: 1, minHeight: 24, backgroundColor: theme.colors.borderSubtle }} /> : null}
              </View>
              <View style={{ flex: 1, paddingBottom: isLast ? 0 : theme.spacing.sm }}>
                <AppText
                  variant="bodyStrong"
                  color={state === "pending" ? "secondary" : "primary"}
                  accessibilityLabel={`${step.label}: ${state === "complete" ? "done" : state === "active" ? "in progress" : "not started yet"}`}
                >
                  {step.label}
                </AppText>
                <AppText variant="bodySmall" color="secondary">{step.description}</AppText>
              </View>
            </View>
          );
        })}
      </View>
    </AppCard>
  );
}
