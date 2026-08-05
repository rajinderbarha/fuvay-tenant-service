import React from "react";
import { View } from "react-native";
import { useTheme } from "../../design-system/theme";
import { AppText } from "../AppText";
import { AppButton } from "../AppButton";
import { Icon } from "../Icon";

export interface SaveProfilePanelProps {
  dirty: boolean;
  saving: boolean;
  canSave: boolean;
  onDiscard: () => void;
  onSave: () => void;
}

/** Never the hardcoded "Only your profile name will be updated now" --
 * neutral copy that stays true regardless of which fields this screen
 * eventually surfaces (spec section 10). */
export function SaveProfilePanel({ dirty, saving, canSave, onDiscard, onSave }: SaveProfilePanelProps) {
  const { theme } = useTheme();
  return (
    <View style={{ gap: theme.spacing.sm }}>
      {dirty ? (
        <View style={{ flexDirection: "row", alignItems: "center", justifyContent: "space-between" }}>
          <View style={{ flexDirection: "row", alignItems: "center", gap: theme.spacing.xxs }}>
            <View style={{ width: 6, height: 6, borderRadius: theme.radius.radiusFull, backgroundColor: theme.colors.brandPrimary }} />
            <AppText variant="bodySmall" color="secondary">You have unsaved changes</AppText>
          </View>
          <AppText variant="labelStrong" color="link" onPress={onDiscard} accessibilityRole="button">Discard</AppText>
        </View>
      ) : null}
      <AppButton
        label="Save changes" onPress={onSave} loading={saving}
        disabled={!dirty || !canSave || saving}
      />
      <View style={{ flexDirection: "row", alignItems: "center", gap: theme.spacing.xxs, justifyContent: "center" }}>
        <Icon name="lock-closed-outline" size="compact" color={theme.colors.textTertiary} decorative />
        <AppText variant="caption" color="tertiary">Your changes will be saved to your Fuvay profile.</AppText>
      </View>
    </View>
  );
}
