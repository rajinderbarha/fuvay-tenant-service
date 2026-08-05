import React from "react";
import { View } from "react-native";
import { useTheme } from "../../design-system/theme";
import { AppText } from "../AppText";
import { AppButton } from "../AppButton";
import { AppCard } from "../AppCard";
import { Icon } from "../Icon";

export interface SecurityRemediationCardProps {
  onReviewSessions: () => void;
  onChangePassword: () => void;
}

/** Both actions navigate to the existing canonical screens -- never a
 * second password-change or session implementation (spec section 15). */
export function SecurityRemediationCard({ onReviewSessions, onChangePassword }: SecurityRemediationCardProps) {
  const { theme } = useTheme();
  return (
    <AppCard style={{ gap: theme.spacing.sm }}>
      <View style={{ flexDirection: "row", gap: theme.spacing.sm, alignItems: "flex-start" }}>
        <Icon name="help-circle-outline" size="standard" color={theme.colors.textSecondary} decorative />
        <View style={{ flex: 1 }}>
          <AppText variant="bodyStrong">Don't recognize an activity?</AppText>
          <AppText variant="bodySmall" color="secondary">Review your sessions and update your password.</AppText>
        </View>
      </View>
      <AppButton label="Review sessions" onPress={onReviewSessions} fullWidth />
      <AppButton label="Change password" tone="secondary" onPress={onChangePassword} fullWidth />
    </AppCard>
  );
}
