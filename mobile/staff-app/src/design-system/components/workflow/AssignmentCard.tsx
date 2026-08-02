import React from "react";
import { View } from "react-native";
import { useTheme } from "../../themes";
import { AppText } from "../typography/AppText";
import { Card } from "../foundation/Layout";
import { PrimaryButton, SecondaryButton } from "../actions/Buttons";
import { CustomerAlias } from "../data-display/Privacy";

export interface AssignmentCardProps {
  jobNumber: string;
  serviceName: string;
  customerAlias: string;
  scheduleLabel: string;
  onAccept: () => void;
  onDecline: () => void;
  loading?: boolean;
}

/** New-assignment acknowledgement card (accept/decline) -- purely
 * presentational, the feature layer owns the actual API calls. */
export function AssignmentCard({ jobNumber, serviceName, customerAlias, scheduleLabel, onAccept, onDecline, loading }: AssignmentCardProps) {
  const { theme } = useTheme();
  return (
    <Card>
      <AppText variant="bodyStrong" style={{ marginBottom: 2 }}>{jobNumber} · {serviceName}</AppText>
      <View style={{ flexDirection: "row", justifyContent: "space-between", marginBottom: theme.spacing.base }}>
        <CustomerAlias alias={customerAlias} />
        <AppText variant="caption" color="tertiary">{scheduleLabel}</AppText>
      </View>
      <View style={{ flexDirection: "row", gap: theme.spacing.sm }}>
        <View style={{ flex: 1 }}><SecondaryButton label="Decline" onPress={onDecline} disabled={loading} fullWidth /></View>
        <View style={{ flex: 1 }}><PrimaryButton label="Accept" onPress={onAccept} loading={loading} fullWidth /></View>
      </View>
    </Card>
  );
}
