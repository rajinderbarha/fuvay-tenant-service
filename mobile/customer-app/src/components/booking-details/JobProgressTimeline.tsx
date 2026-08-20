import React from "react";
import { View } from "react-native";
import { useTheme } from "../../design-system/theme";
import { AppText } from "../AppText";
import { AppCard } from "../AppCard";
import { Icon } from "../Icon";
import { ActiveJobStage, JOB_PROGRESS_STEPS, resolveJobProgressStepState } from "../../domain/activeJobPresentation";
import type { WorkflowStageDto } from "../../api/contracts/customerBookings";

/** Mission's 5-step vertical "Job progress" timeline (Booked, Assigned,
 * Scheduled, On the way, Arrived). Only rendered once a real job has
 * reached one of the three stages this phase owns -- `activeStage` is
 * never derived from time or guesswork, only from `resolveActiveJobStage`.
 * A non-color status signal (check / dot / empty ring) accompanies every
 * step so status is never conveyed by color alone. */
type JobStepState = "complete" | "active" | "pending" | "skipped";

export function JobProgressTimeline({ activeStage, stages }: {
  activeStage: ActiveJobStage | "arrived";
  /** Customer-visible steps of this job's configured workflow. When present
   *  they replace the fixed five-step list: the journey an admin defined is
   *  what the customer should see, and its progress is computed server-side
   *  from the job's real event history rather than re-derived here. */
  stages?: readonly WorkflowStageDto[];
}) {
  const { theme } = useTheme();
  const useWorkflow = !!stages && stages.length > 0;
  const steps = useWorkflow
    ? stages!.map(s => ({ key: s.step_key, label: s.label, description: "" }))
    : JOB_PROGRESS_STEPS;
  return (
    <AppCard>
      <AppText variant="labelStrong" color="secondary">Job progress</AppText>
      <View
        style={{ marginTop: theme.spacing.sm }}
        accessible
        accessibilityRole="progressbar"
        accessibilityLabel="Job progress"
      >
        {steps.map((step, i) => {
          // A workflow step already carries the state the server computed; only
          // the fallback list needs deriving from activeStage.
          const state: JobStepState = useWorkflow
            ? ({ completed: "complete", current: "active", skipped: "skipped", upcoming: "pending" } as const)[stages![i].state]
            : resolveJobProgressStepState(step.key, activeStage);
          const isLast = i === steps.length - 1;
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
                  accessibilityLabel={`${step.label}: ${state === "complete" ? "done" : state === "active" ? "in progress" : state === "skipped" ? "skipped" : "not started yet"}`}
                >
                  {step.label}
                </AppText>
                {step.description ? (
                  <AppText variant="bodySmall" color="secondary">{step.description}</AppText>
                ) : state === "skipped" ? (
                  <AppText variant="bodySmall" color="secondary">Not needed for this job</AppText>
                ) : null}
              </View>
            </View>
          );
        })}
      </View>
    </AppCard>
  );
}
