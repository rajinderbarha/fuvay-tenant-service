import React from "react";
import { View } from "react-native";
import { useTheme } from "../../design-system/theme";
import { AppText } from "../AppText";
import { AppIconButton } from "../AppIconButton";
import { Icon } from "../Icon";

export interface AssistantHeaderProps {
  title: string;
  onClose: () => void;
  /** Discards the current conversation and starts a genuinely fresh
   * request for the same service -- the explicit "start again" escape
   * hatch for a conversation that has gone somewhere the customer didn't
   * intend. */
  onRestart?: () => void;
}

export function AssistantHeader({ title, onClose, onRestart }: AssistantHeaderProps) {
  const { theme } = useTheme();
  return (
    <View style={{ gap: theme.spacing.xs }}>
      <View style={{ flexDirection: "row", alignItems: "center", gap: theme.spacing.xs }}>
        <AppIconButton name="chevron-back" onPress={onClose} accessibilityLabel="Back" />
        <View
          style={{
            width: 28, height: 28, borderRadius: theme.radius.radiusFull,
            backgroundColor: theme.colors.brandPrimaryMuted,
            alignItems: "center", justifyContent: "center",
          }}
        >
          <Icon name="sparkles" size="compact" color={theme.colors.brandPrimaryStrong} decorative />
        </View>
        <View style={{ flex: 1 }}>
          <AppText variant="headingSmall" numberOfLines={1}>{title}</AppText>
          <AppText variant="caption" color="tertiary">Saved automatically</AppText>
        </View>
        {onRestart ? (
          <AppIconButton name="refresh" onPress={onRestart} accessibilityLabel="Start a new request" />
        ) : null}
        <AppIconButton name="close" onPress={onClose} accessibilityLabel="Close assistant" />
      </View>
    </View>
  );
}
