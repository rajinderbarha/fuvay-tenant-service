import React from "react";
import { View } from "react-native";
import { useTheme } from "../../design-system/theme";
import { AppText } from "../AppText";
import { AppButton } from "../AppButton";
import { Icon } from "../Icon";

export interface SignOutCardProps {
  onSignOut: () => void;
  signingOut: boolean;
}

export function SignOutCard({ onSignOut, signingOut }: SignOutCardProps) {
  const { theme } = useTheme();
  return (
    <View
      style={{
        borderWidth: 1, borderColor: theme.colors.statusDanger, borderRadius: theme.radiusUsage.card,
        padding: theme.layout.cardPadding,
      }}
    >
      <AppButton
        label="Sign out"
        tone="destructive"
        onPress={onSignOut}
        loading={signingOut}
        disabledReason={undefined}
      />
      <View style={{ flexDirection: "row", alignItems: "center", gap: theme.spacing.xxs, marginTop: theme.spacing.xs }}>
        <Icon name="log-out-outline" size="compact" color={theme.colors.textTertiary} decorative />
        <AppText variant="caption" color="tertiary">You can sign in again anytime.</AppText>
      </View>
    </View>
  );
}
