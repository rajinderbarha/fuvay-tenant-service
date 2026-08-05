import React from "react";
import { View } from "react-native";
import { useTheme } from "../../design-system/theme";
import { AppText } from "../AppText";
import { AppCard } from "../AppCard";
import { AppBadge } from "../AppBadge";
import { Icon, IconProps } from "../Icon";
import { PrivacyRequestPresentation } from "../../domain/privacyRequestPresentation";

const TONE_ICON: Record<PrivacyRequestPresentation["tone"], IconProps["name"]> = {
  success: "shield-checkmark-outline",
  warning: "time-outline",
  danger: "alert-circle-outline",
  info: "shield-outline",
  neutral: "help-circle-outline",
};

const TONE_KEYS: Record<PrivacyRequestPresentation["tone"], { fg: string; bg: string; border: string }> = {
  success: { fg: "statusSuccess", bg: "statusSuccessSurface", border: "statusSuccess" },
  warning: { fg: "statusWarning", bg: "statusWarningSurface", border: "statusWarning" },
  danger: { fg: "statusDanger", bg: "statusDangerSurface", border: "statusDanger" },
  info: { fg: "statusInfo", bg: "statusInfoSurface", border: "statusInfo" },
  neutral: { fg: "statusNeutral", bg: "statusNeutralSurface", border: "borderSubtle" },
};

export function PrivacyRequestStatusCard({ presentation }: { presentation: PrivacyRequestPresentation }) {
  const { theme } = useTheme();
  const colors = theme.colors as unknown as Record<string, string>;
  const keys = TONE_KEYS[presentation.tone];

  return (
    <AppCard
      style={{ gap: theme.spacing.xs, backgroundColor: colors[keys.bg], borderColor: colors[keys.border], borderWidth: 1 }}
      accessible
      accessibilityLabel={`${presentation.title}. ${presentation.explanation}`}
    >
      <View style={{ flexDirection: "row", gap: theme.spacing.sm, alignItems: "flex-start" }}>
        <Icon name={TONE_ICON[presentation.tone]} size="feature" color={colors[keys.fg]} decorative />
        <View style={{ flex: 1, gap: theme.spacing.xxs }}>
          <AppText variant="bodyStrong" style={{ color: colors[keys.fg] }}>{presentation.title}</AppText>
          <AppText variant="bodySmall" color="secondary">{presentation.explanation}</AppText>
          <View style={{ marginTop: theme.spacing.xxs, alignSelf: "flex-start" }}>
            <AppBadge label={presentation.typeLabel} tone={presentation.tone} />
          </View>
        </View>
      </View>
    </AppCard>
  );
}
