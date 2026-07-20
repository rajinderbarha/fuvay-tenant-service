import React from "react";
import { View } from "react-native";
import { AppText } from "../primitives/AppText";
import { AppButton } from "../primitives/AppButton";
import { AppIcon, type IconName } from "../primitives/AppIcon";
import { useAppTheme } from "../../design-system/themes/use-app-theme";

export interface EmptyStateAction {
  label: string;
  onPress: () => void;
}

export interface EmptyStateProps {
  title: string;
  description?: string;
  icon?: IconName;
  primaryAction?: EmptyStateAction;
  secondaryAction?: EmptyStateAction;
}

export function EmptyState({ title, description, icon = "search", primaryAction, secondaryAction }: EmptyStateProps) {
  const { theme } = useAppTheme();

  return (
    <View style={{ alignItems: "center", paddingVertical: theme.spacing[10], paddingHorizontal: theme.spacing[7], gap: theme.spacing[4] }}>
      <AppIcon name={icon} size="xl" color="iconSecondary" />
      <AppText variant="titleLarge" align="center">
        {title}
      </AppText>
      {description ? (
        <AppText variant="bodyMedium" color="textSecondary" align="center">
          {description}
        </AppText>
      ) : null}
      {primaryAction ? <AppButton label={primaryAction.label} onPress={primaryAction.onPress} variant="primary" size="medium" /> : null}
      {secondaryAction ? <AppButton label={secondaryAction.label} onPress={secondaryAction.onPress} variant="text" size="medium" /> : null}
    </View>
  );
}
