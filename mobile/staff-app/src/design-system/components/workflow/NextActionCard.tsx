import React from "react";
import { View } from "react-native";
import { useTheme } from "../../themes";
import { AppText } from "../typography/AppText";
import { Card } from "../foundation/Layout";
import { PrimaryButton, SecondaryButton, DestructiveButton } from "../actions/Buttons";
import { ActionPresentationModel } from "../../types";

export interface NextActionCardProps {
  title: string;
  description?: string;
  action: ActionPresentationModel;
  /** Feature layer maps `action.code` to the real handler -- this
   * component only renders the button and forwards the press. */
  onPress: () => void;
}

/**
 * Renders exactly one backend-driven "next required action". Never derives
 * the action itself by comparing status strings -- `action` must come from
 * the execution-workspace API projection.
 */
export function NextActionCard({ title, description, action, onPress }: NextActionCardProps) {
  const { theme } = useTheme();
  const ButtonComponent = action.tone === "danger" ? DestructiveButton : action.tone === "secondary" ? SecondaryButton : PrimaryButton;

  return (
    <Card style={{ backgroundColor: theme.colors.brandPrimaryMuted, borderColor: "transparent" }}>
      <View style={{ marginBottom: theme.spacing.sm }}>
        <AppText variant="bodyStrong">{title}</AppText>
        {description ? <AppText variant="bodySmall" color="secondary">{description}</AppText> : null}
      </View>
      <ButtonComponent
        label={action.label}
        onPress={onPress}
        disabled={!action.enabled}
        loading={action.loading}
        disabledReason={action.disabledReason}
        fullWidth
      />
    </Card>
  );
}
