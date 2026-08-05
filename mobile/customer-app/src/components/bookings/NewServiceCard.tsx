import React from "react";
import { View, Pressable } from "react-native";
import { useTheme } from "../../design-system/theme";
import { AppText } from "../AppText";
import { AppCard } from "../AppCard";
import { Icon } from "../Icon";

export interface NewServiceCardProps {
  onPress: () => void;
}

export function NewServiceCard({ onPress }: NewServiceCardProps) {
  const { theme } = useTheme();
  return (
    <Pressable onPress={onPress} accessibilityRole="button" accessibilityLabel="Start a new service request with Fuvay Assistant">
      <AppCard>
        <View style={{ flexDirection: "row", alignItems: "center", gap: theme.spacing.sm }}>
          <View style={{ width: 40, height: 40, borderRadius: theme.radius.radiusFull, backgroundColor: theme.colors.brandPrimaryMuted, alignItems: "center", justifyContent: "center" }}>
            <Icon name="sparkles" size="standard" color={theme.colors.brandPrimaryStrong} decorative />
          </View>
          <View style={{ flex: 1 }}>
            <AppText variant="bodyStrong">Need help with something else?</AppText>
            <AppText variant="bodySmall" color="secondary">Start a new service request with Fuvay Assistant.</AppText>
          </View>
          <AppText variant="labelStrong" color="link">Start assistant</AppText>
        </View>
      </AppCard>
    </Pressable>
  );
}
