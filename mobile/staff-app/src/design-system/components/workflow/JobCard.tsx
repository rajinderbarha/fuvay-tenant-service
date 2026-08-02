import React from "react";
import { View, Pressable } from "react-native";
import { useTheme } from "../../themes";
import { AppText } from "../typography/AppText";
import { Card } from "../foundation/Layout";
import { StatusBadge } from "../data-display/Badges";
import { CustomerAlias } from "../data-display/Privacy";
import { Icon } from "../Icon";

export interface JobCardModel {
  jobId: string;
  jobNumber: string;
  serviceName: string;
  customerAlias: string;
  scheduleLabel: string;
  locationLabel?: string;
  statusCode: string;
}

export interface JobCardProps {
  job: JobCardModel;
  onPress: (jobId: string) => void;
}

/** JobCard -- a row in JobsList (Today/Active/Upcoming/Completed). Purely
 * presentational; the feature layer supplies the already-fetched model
 * and handles navigation on press. */
export function JobCard({ job, onPress }: JobCardProps) {
  const { theme } = useTheme();
  return (
    <Pressable onPress={() => onPress(job.jobId)} accessibilityRole="button" accessibilityLabel={`Job ${job.jobNumber}, ${job.serviceName}`}>
      <Card>
        <View style={{ flexDirection: "row", justifyContent: "space-between", alignItems: "flex-start", marginBottom: theme.spacing.xs }}>
          <AppText variant="bodyStrong">{job.jobNumber}</AppText>
          <StatusBadge statusCode={job.statusCode} />
        </View>
        <AppText variant="body" color="secondary" style={{ marginBottom: theme.spacing.xs }}>{job.serviceName}</AppText>
        <View style={{ flexDirection: "row", justifyContent: "space-between", alignItems: "center" }}>
          <CustomerAlias alias={job.customerAlias} />
          <AppText variant="caption" color="tertiary">{job.scheduleLabel}</AppText>
        </View>
        {job.locationLabel ? (
          <View style={{ flexDirection: "row", alignItems: "center", gap: 4, marginTop: theme.spacing.xs }}>
            <Icon name="location-outline" size="compact" color={theme.colors.textTertiary} decorative />
            <AppText variant="caption" color="tertiary">{job.locationLabel}</AppText>
          </View>
        ) : null}
      </Card>
    </Pressable>
  );
}
