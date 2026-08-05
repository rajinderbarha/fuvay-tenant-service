import React from "react";
import { View } from "react-native";
import { useTheme } from "../design-system/theme";
import { AppText } from "./AppText";

export type BadgeTone = "success" | "warning" | "danger" | "info" | "neutral";

const TONE_KEYS: Record<BadgeTone, { fg: string; bg: string }> = {
  success: { fg: "statusSuccess", bg: "statusSuccessSurface" },
  warning: { fg: "statusWarning", bg: "statusWarningSurface" },
  danger: { fg: "statusDanger", bg: "statusDangerSurface" },
  info: { fg: "statusInfo", bg: "statusInfoSurface" },
  neutral: { fg: "statusNeutral", bg: "statusNeutralSurface" },
};

export interface AppBadgeProps {
  label: string;
  tone?: BadgeTone;
}

/** Status pill. Tone drives color exclusively through the semantic status
 * tokens -- success/warning/danger/info/neutral only, never a decorative
 * color choice. */
export function AppBadge({ label, tone = "neutral" }: AppBadgeProps) {
  const { theme } = useTheme();
  const keys = TONE_KEYS[tone];
  const colors = theme.colors as unknown as Record<string, string>;
  return (
    <View
      style={{
        alignSelf: "flex-start",
        paddingHorizontal: theme.spacing.sm,
        paddingVertical: theme.spacing.xxs,
        borderRadius: theme.radiusUsage.statusPill,
        backgroundColor: colors[keys.bg],
      }}
    >
      <AppText variant="labelStrong" style={{ color: colors[keys.fg] }}>{label}</AppText>
    </View>
  );
}
