import React from "react";
import { View, Alert } from "react-native";
import { useTheme } from "../../design-system/theme";
import { AppText } from "../AppText";
import { Icon } from "../Icon";

export interface GlobalSignOutRowProps {
  onConfirm: () => void;
  pending: boolean;
}

export function GlobalSignOutRow({ onConfirm, pending }: GlobalSignOutRowProps) {
  const { theme } = useTheme();

  function handlePress() {
    Alert.alert(
      "Sign out of all devices?",
      "All active sessions, including this device, will be signed out. You will need to sign in again.",
      [
        { text: "Keep me signed in", style: "cancel" },
        { text: "Sign out all", style: "destructive", onPress: onConfirm },
      ],
    );
  }

  return (
    <View>
      <View
        style={{
          flexDirection: "row", alignItems: "center", gap: theme.spacing.sm,
          paddingVertical: theme.spacing.sm, paddingHorizontal: theme.spacing.sm,
          borderRadius: theme.radiusUsage.card, borderWidth: 1, borderColor: theme.colors.statusDanger,
        }}
      >
        <Icon name="log-out-outline" size="standard" color={theme.colors.statusDanger} decorative />
        <View style={{ flex: 1 }}>
          <AppText
            variant="bodyStrong" style={{ color: theme.colors.statusDanger }}
            onPress={pending ? undefined : handlePress} accessibilityRole="button"
            accessibilityLabel="Sign out of all devices"
          >
            Sign out of all devices
          </AppText>
          <AppText variant="caption" color="secondary">You will need to sign in again.</AppText>
        </View>
      </View>
      {pending ? <AppText variant="caption" color="secondary" align="center" style={{ marginTop: theme.spacing.xs }}>Signing out your sessions…</AppText> : null}
    </View>
  );
}
