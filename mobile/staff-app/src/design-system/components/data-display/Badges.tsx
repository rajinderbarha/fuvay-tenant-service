import React from "react";
import { View } from "react-native";
import { useTheme } from "../../themes";
import { AppText } from "../typography/AppText";
import { resolveWorkflowStatus, workflowToneColor, WorkflowTone } from "../../workflowStatus";

function toneSurfaceColor(theme: ReturnType<typeof useTheme>["theme"], tone: WorkflowTone) {
  switch (tone) {
    case "completed": return theme.colors.statusSuccessSurface;
    case "current": return theme.colors.brandPrimaryMuted;
    case "blocked": return theme.colors.statusDangerSurface;
    case "cancelled": return theme.colors.surfaceDisabled;
    default: return theme.colors.statusNeutralSurface;
  }
}

/**
 * StatusBadge -- the ONLY place a backend job-status string is converted to
 * a label/color. Always routes through the centralized WORKFLOW_STATUS_MAP
 * (never a second mapping inside a screen). Unknown statuses render the
 * safe neutral fallback and never imply an available action.
 */
export function StatusBadge({ statusCode }: { statusCode: string }) {
  const { theme } = useTheme();
  const entry = resolveWorkflowStatus(statusCode);
  const fg = workflowToneColor(theme, entry.tone);
  return (
    <View
      accessibilityRole="text"
      accessibilityLabel={`Status: ${entry.label}. ${entry.description}`}
      style={{
        alignSelf: "flex-start", paddingHorizontal: theme.spacing.sm, paddingVertical: 4,
        borderRadius: theme.radiusUsage.statusPill, backgroundColor: toneSurfaceColor(theme, entry.tone),
      }}
    >
      <AppText variant="labelStrong" style={{ color: fg }}>{entry.label}</AppText>
    </View>
  );
}

export type Priority = "low" | "normal" | "high" | "urgent";

const PRIORITY_LABEL: Record<Priority, string> = { low: "Low", normal: "Normal", high: "High", urgent: "Urgent" };

export function PriorityBadge({ priority }: { priority: Priority }) {
  const { theme } = useTheme();
  const tone = priority === "urgent" || priority === "high" ? theme.colors.statusDanger : theme.colors.statusNeutral;
  const bg = priority === "urgent" || priority === "high" ? theme.colors.statusDangerSurface : theme.colors.statusNeutralSurface;
  return (
    <View
      accessibilityRole="text"
      accessibilityLabel={`Priority: ${PRIORITY_LABEL[priority]}`}
      style={{ alignSelf: "flex-start", paddingHorizontal: theme.spacing.sm, paddingVertical: 4, borderRadius: theme.radiusUsage.statusPill, backgroundColor: bg }}
    >
      <AppText variant="labelStrong" style={{ color: tone }}>{PRIORITY_LABEL[priority]}</AppText>
    </View>
  );
}
