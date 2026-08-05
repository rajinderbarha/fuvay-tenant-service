import React from "react";
import { View } from "react-native";
import { useTheme } from "../../design-system/theme";
import { AppText } from "../AppText";
import { AppCard } from "../AppCard";
import { Icon } from "../Icon";
import { ActiveJobPresentation } from "../../domain/activeJobPresentation";

const TONE_ICON: Record<ActiveJobPresentation["tone"], React.ComponentProps<typeof Icon>["name"]> = {
  info: "person-outline",
  warning: "car-outline",
};

export interface ActiveJobStatusCardProps {
  presentation: ActiveJobPresentation;
  scheduleText: string | null;
}

/** Mission's "Primary status section" for the three job-driven states this
 * phase owns. Renders only the passed-in, already-resolved presentation --
 * never a raw backend status string. `scheduleText` is omitted entirely
 * (not shown as a blank/placeholder row) when the backend has no verified
 * schedule yet. */
export function ActiveJobStatusCard({ presentation, scheduleText }: ActiveJobStatusCardProps) {
  const { theme } = useTheme();
  const toneColor = presentation.tone === "warning" ? theme.colors.statusWarning : theme.colors.brandPrimary;
  const toneSurface = presentation.tone === "warning" ? theme.colors.statusWarningSurface : theme.colors.brandPrimaryMuted;

  return (
    <AppCard style={{ borderColor: toneColor, borderWidth: 1 }}>
      <View style={{ flexDirection: "row", gap: theme.spacing.sm, alignItems: "flex-start" }}>
        <View
          style={{
            width: 44, height: 44, borderRadius: theme.radiusUsage.card, alignItems: "center", justifyContent: "center",
            backgroundColor: toneSurface,
          }}
        >
          <Icon name={TONE_ICON[presentation.tone]} size="standard" color={toneColor} decorative />
        </View>
        <View style={{ flex: 1, gap: theme.spacing.xxs }}>
          <AppText variant="bodyStrong" accessibilityRole="header">{presentation.title}</AppText>
          <AppText variant="bodySmall" color="secondary">{presentation.explanation}</AppText>
          {scheduleText ? (
            <AppText variant="labelStrong" style={{ color: toneColor, marginTop: theme.spacing.xxs }}>{scheduleText}</AppText>
          ) : null}
        </View>
      </View>
    </AppCard>
  );
}
