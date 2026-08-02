import React from "react";
import { View } from "react-native";
import { useTheme } from "../../themes";
import { AppText } from "../typography/AppText";
import { Icon } from "../Icon";
import { SemanticTone } from "../../types";

function toneVisuals(theme: ReturnType<typeof useTheme>["theme"], tone: SemanticTone) {
  const { colors } = theme;
  switch (tone) {
    case "success": return { bg: colors.statusSuccessSurface, fg: colors.statusSuccess, icon: "checkmark-circle" as const };
    case "warning": return { bg: colors.statusWarningSurface, fg: colors.statusWarning, icon: "warning" as const };
    case "danger":  return { bg: colors.statusDangerSurface,  fg: colors.statusDanger,  icon: "alert-circle" as const };
    case "info":    return { bg: colors.statusInfoSurface,    fg: colors.statusInfo,    icon: "information-circle" as const };
    default:        return { bg: colors.statusNeutralSurface, fg: colors.statusNeutral, icon: "ellipse" as const };
  }
}

export interface InlineAlertProps {
  tone: SemanticTone;
  title?: string;
  message: string;
}

/** Generic inline alert -- neutral/info/success/warning/danger. Meaning is
 * conveyed by icon + text, never color alone. */
export function InlineAlert({ tone, title, message }: InlineAlertProps) {
  const { theme } = useTheme();
  const v = toneVisuals(theme, tone);
  return (
    <View
      accessibilityRole="alert"
      style={{
        flexDirection: "row", gap: theme.spacing.sm, padding: theme.spacing.base,
        borderRadius: theme.radiusUsage.card, backgroundColor: v.bg,
      }}
    >
      <Icon name={v.icon} size="standard" color={v.fg} decorative />
      <View style={{ flex: 1 }}>
        {title ? <AppText variant="bodyStrong" style={{ color: v.fg, marginBottom: 2 }}>{title}</AppText> : null}
        <AppText variant="bodySmall" style={{ color: v.fg }}>{message}</AppText>
      </View>
    </View>
  );
}

export function ErrorBanner({ message }: { message: string }) {
  return <InlineAlert tone="danger" title="Something went wrong" message={message} />;
}

export function SuccessBanner({ message }: { message: string }) {
  return <InlineAlert tone="success" message={message} />;
}

/** OfflineBanner -- shown by the network-status provider (Phase F), not
 * fetched here; purely presentational. */
export function OfflineBanner({ lastSyncedLabel }: { lastSyncedLabel?: string }) {
  return (
    <InlineAlert
      tone="neutral"
      title="You're offline"
      message={lastSyncedLabel ? `Showing data from ${lastSyncedLabel}. Some actions require a connection.` : "Some actions require a connection."}
    />
  );
}

export interface BlockingBannerProps {
  title: string;
  message: string;
  /** Raw backend block code -- shown for support/debugging, not
   * interpreted into a business action here. */
  blockCode?: string;
  permittedNextActionLabel?: string;
  severity?: "info" | "warning" | "danger";
}

/**
 * A workflow-blocking condition (e.g. ESTIMATE_APPROVAL_REQUIRED). Never
 * converts the block code into a business action itself -- the feature
 * layer maps block codes to real actions (spec section 6/17).
 */
export function BlockingBanner({ title, message, blockCode, permittedNextActionLabel, severity = "warning" }: BlockingBannerProps) {
  const { theme } = useTheme();
  const v = toneVisuals(theme, severity);
  return (
    <View
      accessibilityRole="alert"
      style={{ padding: theme.spacing.base, borderRadius: theme.radiusUsage.card, backgroundColor: v.bg, gap: theme.spacing.xs }}
    >
      <View style={{ flexDirection: "row", gap: theme.spacing.sm, alignItems: "center" }}>
        <Icon name={v.icon} size="standard" color={v.fg} decorative />
        <AppText variant="bodyStrong" style={{ color: v.fg, flex: 1 }}>{title}</AppText>
      </View>
      <AppText variant="bodySmall" style={{ color: v.fg }}>{message}</AppText>
      {permittedNextActionLabel ? (
        <AppText variant="caption" style={{ color: v.fg, fontStyle: "italic" }}>{permittedNextActionLabel}</AppText>
      ) : null}
      {blockCode ? <AppText variant="caption" color="tertiary">Code: {blockCode}</AppText> : null}
    </View>
  );
}
