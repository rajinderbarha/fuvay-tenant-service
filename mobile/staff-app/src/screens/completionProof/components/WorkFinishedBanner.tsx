import React from "react";
import { View } from "react-native";
import { useTheme } from "../../../design-system/themes";
import { AppText } from "../../../design-system/components/typography/AppText";
import { Icon } from "../../../design-system/components/Icon";
import { WorkSummaryDTO } from "../../../services/completionProof/types";

export function WorkFinishedBanner({ workSummary, checklistLabel }: { workSummary: WorkSummaryDTO; checklistLabel: string }) {
  const { theme } = useTheme();
  const time = workSummary.work_finished_at
    ? new Date(workSummary.work_finished_at).toLocaleTimeString("en-IN", { hour: "2-digit", minute: "2-digit" })
    : null;
  return (
    <View
      style={{
        flexDirection: "row", alignItems: "center", gap: theme.spacing.sm, padding: theme.spacing.base,
        borderRadius: theme.radiusUsage.card, backgroundColor: theme.colors.statusSuccessSurface,
      }}
    >
      <Icon name="checkmark-circle" size="standard" color={theme.colors.statusSuccess} decorative />
      <View style={{ flex: 1 }}>
        <AppText variant="bodyStrong" style={{ color: theme.colors.statusSuccess }}>Work finished</AppText>
        <AppText variant="caption" style={{ color: theme.colors.statusSuccess }}>
          {checklistLabel}{time ? ` · ${time}` : ""}
        </AppText>
      </View>
    </View>
  );
}
