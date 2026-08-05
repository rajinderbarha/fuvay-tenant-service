import React from "react";
import { View } from "react-native";
import { useTheme } from "../../design-system/theme";
import { AppText } from "../AppText";
import { AppBadge } from "../AppBadge";
import { Icon } from "../Icon";

export interface TwoStepRowProps {
  /** Real backend state only (`User.is_mfa_enabled`) -- never inferred
   * from a single login's MFA challenge (spec section 5). */
  enabled: boolean;
  canSetup: boolean;
  canDisable: boolean;
  onSetup: () => void;
  onManage: () => void;
}

export function TwoStepRow({ enabled, canSetup, canDisable, onSetup, onManage }: TwoStepRowProps) {
  const { theme } = useTheme();
  return (
    <View style={{ flexDirection: "row", alignItems: "center", gap: theme.spacing.sm, paddingVertical: theme.spacing.xs }}>
      <View style={{ width: 36, alignItems: "center" }}>
        <Icon name="checkmark-circle-outline" size="standard" color={theme.colors.textSecondary} decorative />
      </View>
      <View style={{ flex: 1 }}>
        <AppText variant="bodyStrong">Two-step verification</AppText>
        <AppText variant="bodySmall" color="secondary">Extra protection when signing in</AppText>
      </View>
      <View style={{ alignItems: "flex-end", gap: theme.spacing.xxs }}>
        {enabled ? <AppBadge label="Enabled" tone="success" /> : <AppBadge label="Not enabled" tone="neutral" />}
        {!enabled && canSetup ? (
          <AppText variant="labelStrong" color="link" onPress={onSetup} accessibilityRole="button" accessibilityLabel="Set up two-step verification">
            Set up
          </AppText>
        ) : null}
        {enabled && canDisable ? (
          <AppText variant="labelStrong" color="link" onPress={onManage} accessibilityRole="button" accessibilityLabel="Manage two-step verification">
            Manage
          </AppText>
        ) : null}
      </View>
    </View>
  );
}
