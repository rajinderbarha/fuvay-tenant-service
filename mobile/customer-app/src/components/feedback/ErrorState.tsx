import React from "react";
import { View } from "react-native";
import { AppText } from "../primitives/AppText";
import { AppButton } from "../primitives/AppButton";
import { AppIcon } from "../primitives/AppIcon";
import { useAppTheme } from "../../design-system/themes/use-app-theme";

export type ErrorStateMode = "recoverable" | "offline" | "permission-denied";

export interface ErrorStateProps {
  mode?: ErrorStateMode;
  title: string;
  description?: string;
  errorReferenceId?: string;
  onRetry?: () => void;
  onContactSupport?: () => void;
}

const ICON_BY_MODE = {
  recoverable: "alert-circle",
  offline: "cloud-offline",
  "permission-denied": "close-circle",
} as const;

export function ErrorState({ mode = "recoverable", title, description, errorReferenceId, onRetry, onContactSupport }: ErrorStateProps) {
  const { theme } = useAppTheme();

  return (
    <View
      accessible
      accessibilityRole="alert"
      style={{ alignItems: "center", paddingVertical: theme.spacing[10], paddingHorizontal: theme.spacing[7], gap: theme.spacing[4] }}
    >
      <AppIcon name={ICON_BY_MODE[mode]} size="xl" color="iconDanger" />
      <AppText variant="titleLarge" align="center">
        {title}
      </AppText>
      {description ? (
        <AppText variant="bodyMedium" color="textSecondary" align="center">
          {description}
        </AppText>
      ) : null}
      {errorReferenceId ? (
        <AppText variant="caption" color="textTertiary" align="center">
          Reference: {errorReferenceId}
        </AppText>
      ) : null}
      {onRetry ? <AppButton label="Retry" onPress={onRetry} variant="primary" size="medium" /> : null}
      {onContactSupport ? <AppButton label="Contact support" onPress={onContactSupport} variant="text" size="medium" /> : null}
    </View>
  );
}
