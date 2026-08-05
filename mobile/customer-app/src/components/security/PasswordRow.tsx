import React from "react";
import { View } from "react-native";
import { useTheme } from "../../design-system/theme";
import { AppText } from "../AppText";
import { Icon } from "../Icon";

export interface PasswordRowProps {
  onChange: () => void;
}

/** `canChangePassword` gates whether this row renders at all -- there is
 * no "password not set" state for a customer account (every customer
 * authenticates with a password by construction), so only the
 * `Change` variant applies here (spec section 5). */
export function PasswordRow({ onChange }: PasswordRowProps) {
  const { theme } = useTheme();
  return (
    <View style={{ flexDirection: "row", alignItems: "center", gap: theme.spacing.sm, paddingVertical: theme.spacing.xs }}>
      <View style={{ width: 36, alignItems: "center" }}>
        <Icon name="key-outline" size="standard" color={theme.colors.textSecondary} decorative />
      </View>
      <View style={{ flex: 1 }}>
        <AppText variant="bodyStrong">Password</AppText>
        <AppText variant="bodySmall" color="secondary">Password is set</AppText>
      </View>
      <AppText variant="labelStrong" color="link" onPress={onChange} accessibilityRole="button" accessibilityLabel="Change password">
        Change
      </AppText>
    </View>
  );
}
