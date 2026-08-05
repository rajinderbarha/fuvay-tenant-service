import React from "react";
import { Pressable, View } from "react-native";
import { useTheme } from "../../design-system/theme";
import { AppText } from "../AppText";
import { Icon } from "../Icon";

export interface AssistantEntryCardProps {
  onPress: () => void;
}

/**
 * Compact orange-tinted entry point into the existing Assistant tab.
 * Never mentions "DeepSeek," never claims photo diagnosis or
 * general-purpose AI, never starts a booking session here (spec
 * requirements) -- this is purely a navigation affordance.
 */
export function AssistantEntryCard({ onPress }: AssistantEntryCardProps) {
  const { theme } = useTheme();
  return (
    <Pressable
      onPress={onPress}
      accessibilityRole="button"
      accessibilityLabel="Not sure what to book? Tell Fuvay Assistant what's wrong. Start chat."
      style={{
        flexDirection: "row", alignItems: "center", gap: theme.spacing.sm,
        padding: theme.spacing.base, borderRadius: theme.radiusUsage.card,
        backgroundColor: theme.colors.brandPrimaryMuted, borderWidth: 1, borderColor: theme.colors.borderSubtle,
      }}
    >
      <View
        style={{
          width: 40, height: 40, borderRadius: theme.radius.radiusFull,
          backgroundColor: theme.colors.brandPrimary, alignItems: "center", justifyContent: "center",
        }}
      >
        <Icon name="sparkles" size="standard" color={theme.colors.brandOnPrimary} decorative />
      </View>
      <View style={{ flex: 1 }}>
        <AppText variant="bodyStrong">Not sure what to book?</AppText>
        <AppText variant="bodySmall" color="secondary">Tell Fuvay Assistant what's wrong.</AppText>
        <AppText variant="caption" color="tertiary" style={{ marginTop: 2 }}>Guided by available services</AppText>
      </View>
      <View
        style={{
          paddingHorizontal: theme.spacing.sm, paddingVertical: theme.spacing.xs,
          borderRadius: theme.radiusUsage.statusPill, backgroundColor: theme.colors.brandPrimary,
        }}
      >
        <AppText variant="labelStrong" style={{ color: theme.colors.brandOnPrimary }}>Start chat</AppText>
      </View>
    </Pressable>
  );
}
