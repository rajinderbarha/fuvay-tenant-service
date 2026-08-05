import React from "react";
import { View } from "react-native";
import { useTheme } from "../../design-system/theme";
import { AppText } from "../AppText";
import { AppCard } from "../AppCard";
import { Icon } from "../Icon";
import { ArrivalInspectionPresentation } from "../../domain/inspectionQuotePresentation";

const ICON: Record<string, React.ComponentProps<typeof Icon>["name"]> = {
  Arrived: "checkmark-circle-outline",
  "Inspection in progress": "search-outline",
  "Inspection complete": "clipboard-outline",
};

/** Renders the real, backend-derived arrival/inspection state -- title and
 * explanation are both already-resolved, safe strings (never a raw
 * ServiceJob.status enum in JSX). */
export function InspectionStatusCard({ presentation }: { presentation: ArrivalInspectionPresentation }) {
  const { theme } = useTheme();
  return (
    <AppCard style={{ borderColor: theme.colors.brandPrimary, borderWidth: 1 }}>
      <View style={{ flexDirection: "row", gap: theme.spacing.sm, alignItems: "flex-start" }}>
        <View
          style={{
            width: 44, height: 44, borderRadius: theme.radiusUsage.card, alignItems: "center", justifyContent: "center",
            backgroundColor: theme.colors.brandPrimaryMuted,
          }}
        >
          <Icon name={ICON[presentation.title] ?? "information-circle-outline"} size="standard" color={theme.colors.brandPrimaryStrong} decorative />
        </View>
        <View style={{ flex: 1, gap: theme.spacing.xxs }}>
          <AppText variant="bodyStrong" accessibilityRole="header">{presentation.title}</AppText>
          <AppText variant="bodySmall" color="secondary">{presentation.explanation}</AppText>
        </View>
      </View>
    </AppCard>
  );
}
