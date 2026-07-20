import React from "react";
import { View } from "react-native";
import { AppText } from "./AppText";
import { AppIcon, type IconName } from "./AppIcon";
import { useAppTheme } from "../../design-system/themes/use-app-theme";

export type AppBadgeTone = "neutral" | "info" | "success" | "warning" | "danger";

export interface AppBadgeProps {
  label: string;
  tone?: AppBadgeTone;
  icon?: IconName;
}

export function AppBadge({ label, tone = "neutral", icon }: AppBadgeProps) {
  const { theme } = useAppTheme();

  const colors =
    tone === "success"
      ? { bg: theme.colors.statusSuccessBackground, fg: theme.colors.statusSuccessForeground }
      : tone === "warning"
        ? { bg: theme.colors.statusWarningBackground, fg: theme.colors.statusWarningForeground }
        : tone === "danger"
          ? { bg: theme.colors.statusDangerBackground, fg: theme.colors.statusDangerForeground }
          : tone === "info"
            ? { bg: theme.colors.statusInfoBackground, fg: theme.colors.statusInfoForeground }
            : { bg: theme.colors.surfaceSecondary, fg: theme.colors.textSecondary };

  return (
    <View
      accessible
      accessibilityRole="text"
      // Status is communicated via the text label itself, not color alone.
      accessibilityLabel={`${tone !== "neutral" ? `${tone}: ` : ""}${label}`}
      style={{
        flexDirection: "row",
        alignItems: "center",
        gap: 4,
        alignSelf: "flex-start",
        backgroundColor: colors.bg,
        borderRadius: theme.radii.pill,
        paddingHorizontal: theme.spacing[4],
        paddingVertical: theme.spacing[1],
      }}
    >
      {icon ? <AppIcon name={icon} size="xs" color="iconSecondary" /> : null}
      <AppText variant="labelSmall" style={{ color: colors.fg }}>
        {label}
      </AppText>
    </View>
  );
}
