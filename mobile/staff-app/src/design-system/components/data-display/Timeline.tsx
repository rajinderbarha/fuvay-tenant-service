import React from "react";
import { View } from "react-native";
import { useTheme } from "../../themes";
import { AppText } from "../typography/AppText";
import { RelativeTime } from "./DateTimeText";

export interface ActivityRowProps {
  actorLabel: string;
  description: string;
  isoTimestamp: string | null;
}

export function ActivityRow({ actorLabel, description, isoTimestamp }: ActivityRowProps) {
  const { theme } = useTheme();
  return (
    <View style={{ paddingVertical: theme.spacing.xs, gap: 2 }}>
      <AppText variant="bodySmall">{description}</AppText>
      <View style={{ flexDirection: "row", gap: 6 }}>
        <AppText variant="caption" color="tertiary">{actorLabel}</AppText>
        <AppText variant="caption" color="tertiary">·</AppText>
        <RelativeTime isoString={isoTimestamp} variant="caption" color="tertiary" />
      </View>
    </View>
  );
}

export interface TimelineStepProps {
  label: string;
  state: "completed" | "current" | "upcoming" | "blocked" | "skipped";
  isLast?: boolean;
}

function stepColor(theme: ReturnType<typeof useTheme>["theme"], state: TimelineStepProps["state"]) {
  switch (state) {
    case "completed": return theme.colors.workflowCompleted;
    case "current": return theme.colors.workflowCurrent;
    case "blocked": return theme.colors.workflowBlocked;
    case "skipped": return theme.colors.workflowCancelled;
    default: return theme.colors.workflowUpcoming;
  }
}

export function TimelineStep({ label, state, isLast }: TimelineStepProps) {
  const { theme } = useTheme();
  const color = stepColor(theme, state);
  return (
    <View style={{ flexDirection: "row", gap: theme.spacing.sm }}>
      <View style={{ alignItems: "center" }}>
        <View style={{ width: 12, height: 12, borderRadius: 6, backgroundColor: color }} />
        {!isLast ? <View style={{ width: 2, flex: 1, backgroundColor: theme.colors.borderDefault, marginTop: 2 }} /> : null}
      </View>
      <AppText variant="bodySmall" style={{ paddingBottom: theme.spacing.base }} color={state === "upcoming" ? "tertiary" : "primary"}>
        {label}
      </AppText>
    </View>
  );
}

export function Timeline({ steps }: { steps: TimelineStepProps[] }) {
  return (
    <View>
      {steps.map((step, i) => <TimelineStep key={step.label + i} {...step} isLast={i === steps.length - 1} />)}
    </View>
  );
}
