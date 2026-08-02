import React from "react";
import { View, Pressable } from "react-native";
import { useTheme } from "../../../design-system/themes";
import { Card } from "../../../design-system/components/foundation/Layout";
import { AppText } from "../../../design-system/components/typography/AppText";
import { Icon } from "../../../design-system/components/Icon";
import { PrimaryButton, SecondaryButton } from "../../../design-system/components/actions/Buttons";
import { StatusBadge } from "../../../design-system/components/data-display/Badges";
import { CustomerAlias } from "../../../design-system/components/data-display/Privacy";
import { resolveWorkflowStatus } from "../../../design-system/workflowStatus";
import { JobListItemDTO } from "../../../services/jobs/types";

export interface JobListCardProps {
  job: JobListItemDTO;
  onPress: () => void;
  onPrimaryAction: () => void;
}

/**
 * Compact mobile job card (Phase I spec section 3) -- scannable, not a
 * full Job Detail screen. No SLA/due-time claim is rendered: no such
 * backend field exists (audited in Phase H); the card shows only the
 * real scheduled time and workflow status, never a fabricated urgency.
 */
export function JobListCard({ job, onPress, onPrimaryAction }: JobListCardProps) {
  const { theme } = useTheme();
  const statusEntry = resolveWorkflowStatus(job.workflow_status);
  const accessibilityLabel = `Job ${job.job_reference}, ${job.service_label ?? "Service"}, ${statusEntry.label}` +
    (job.scheduled_time_window ? `, scheduled ${job.scheduled_time_window}` : "");

  return (
    <Pressable onPress={onPress} accessibilityRole="button" accessibilityLabel={accessibilityLabel} style={{ minHeight: 44 }}>
      <Card>
        <View style={{ flexDirection: "row", justifyContent: "space-between", alignItems: "flex-start", marginBottom: theme.spacing.xs }}>
          <View style={{ flex: 1 }}>
            <AppText variant="bodyStrong">{job.job_reference} · {job.service_label ?? "Service"}</AppText>
            {job.job_type_label ? <AppText variant="caption" color="tertiary">{job.job_type_label}</AppText> : null}
          </View>
          <StatusBadge statusCode={job.workflow_status} />
        </View>

        <View style={{ flexDirection: "row", alignItems: "center", gap: 4, marginBottom: 2 }}>
          <Icon name="time-outline" size="compact" color={theme.colors.textTertiary} decorative />
          <AppText variant="bodySmall" color="secondary">{job.scheduled_time_window ?? "Unscheduled"}</AppText>
        </View>
        {job.safe_locality ? (
          <View style={{ flexDirection: "row", alignItems: "center", gap: 4, marginBottom: 2 }}>
            <Icon name="location-outline" size="compact" color={theme.colors.textTertiary} decorative />
            <AppText variant="bodySmall" color="secondary">{job.safe_locality}</AppText>
          </View>
        ) : null}
        <View style={{ marginBottom: theme.spacing.sm }}>
          <CustomerAlias alias={job.customer_alias} />
        </View>

        {job.next_required_action.label ? (
          <PrimaryButton label={job.next_required_action.label} onPress={onPrimaryAction} disabled={!job.next_required_action.allowed} fullWidth />
        ) : (
          <SecondaryButton label="View job" onPress={onPress} fullWidth />
        )}
      </Card>
    </Pressable>
  );
}
