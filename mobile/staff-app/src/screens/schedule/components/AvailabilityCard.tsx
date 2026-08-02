import React from "react";
import { View } from "react-native";
import { useTheme } from "../../../design-system/themes";
import { Card } from "../../../design-system/components/foundation/Layout";
import { AppText } from "../../../design-system/components/typography/AppText";
import { AvailabilityState } from "../../../services/home/types";

const LABEL: Record<AvailabilityState, string> = { available: "Available today", busy: "Busy today", offline: "Offline today" };

function toneColor(theme: ReturnType<typeof useTheme>["theme"], state: AvailabilityState) {
  if (state === "available") return theme.colors.statusSuccess;
  if (state === "busy") return theme.colors.statusWarning;
  return theme.colors.textTertiary;
}

/** Live presence (available/busy/offline) is the existing
 * ProviderTeamMember.availability_state -- this card never duplicates it,
 * only summarizes it alongside the day's recurring working-hours label
 * (spec section 4: these stay conceptually separate). */
export function AvailabilityCard({ state, workingHoursLabel, onManage }: { state: AvailabilityState; workingHoursLabel: string | null; onManage: () => void }) {
  const { theme } = useTheme();
  return (
    <Card style={{ flexDirection: "row", alignItems: "center" }}>
      <View style={{ width: 10, height: 10, borderRadius: 5, backgroundColor: toneColor(theme, state), marginRight: theme.spacing.sm }} />
      <View style={{ flex: 1 }}>
        <AppText variant="bodyStrong">{LABEL[state]}</AppText>
        <AppText variant="caption" color="tertiary">{workingHoursLabel ? `Working hours ${workingHoursLabel}` : "No working hours configured"}</AppText>
      </View>
      <AppText variant="bodyStrong" color="link" onPress={onManage} accessibilityRole="button">Manage</AppText>
    </Card>
  );
}
