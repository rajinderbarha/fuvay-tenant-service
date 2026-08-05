import React from "react";
import { View, Alert } from "react-native";
import { useTheme } from "../../design-system/theme";
import { AppText } from "../AppText";
import { AppButton } from "../AppButton";
import { Icon } from "../Icon";

export interface RevokeOtherDevicesFooterProps {
  onConfirm: () => void;
  pending: boolean;
}

/** Only rendered when another active session exists (spec section 10) --
 * the caller decides that, not this component. */
export function RevokeOtherDevicesFooter({ onConfirm, pending }: RevokeOtherDevicesFooterProps) {
  const { theme } = useTheme();

  function handlePress() {
    Alert.alert(
      "Sign out of all other devices?",
      "Every other active session will need to sign in again. This device will remain signed in.",
      [
        { text: "Keep sessions", style: "cancel" },
        { text: "Sign out others", style: "destructive", onPress: onConfirm },
      ],
    );
  }

  return (
    <View style={{ gap: theme.spacing.sm }}>
      <AppButton
        label="Sign out of other devices" tone="destructive" onPress={handlePress}
        loading={pending} fullWidth
        leadingIcon={<Icon name="log-out-outline" size="compact" color={theme.colors.statusDanger} decorative />}
      />
      <AppText variant="caption" color="tertiary" align="center">Your current session will stay signed in.</AppText>
      {pending ? <AppText variant="caption" color="secondary" align="center">Signing out other devices…</AppText> : null}
    </View>
  );
}
