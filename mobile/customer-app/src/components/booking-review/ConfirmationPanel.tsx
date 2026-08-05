import React from "react";
import { View } from "react-native";
import { useTheme } from "../../design-system/theme";
import { AppText } from "../AppText";
import { AppButton } from "../AppButton";
import { Icon } from "../Icon";
import { ConfirmationEligibility, CONFIRMATION_BLOCK_COPY } from "../../domain/confirmationEligibility";

export interface ConfirmationPanelProps {
  eligibility: ConfirmationEligibility;
  confirming: boolean;
  onBackToAssistant: () => void;
  onConfirm: () => void;
}

export function ConfirmationPanel({ eligibility, confirming, onBackToAssistant, onConfirm }: ConfirmationPanelProps) {
  const { theme } = useTheme();
  return (
    <View style={{ gap: theme.spacing.sm }}>
      {!eligibility.allowed && !confirming ? (
        <AppText variant="bodySmall" color="secondary">{CONFIRMATION_BLOCK_COPY[eligibility.reason]}</AppText>
      ) : null}
      <View style={{ flexDirection: "row", alignItems: "center", gap: theme.spacing.xxs }}>
        <Icon name="lock-closed-outline" size="compact" color={theme.colors.textTertiary} decorative />
        <AppText variant="caption" color="tertiary" style={{ flex: 1 }}>
          By confirming, you agree to the service request details shown above.
        </AppText>
      </View>
      <View style={{ flexDirection: "row", alignItems: "center", gap: theme.spacing.sm }}>
        <AppText variant="labelStrong" color="link" onPress={onBackToAssistant}>Back to assistant</AppText>
        <View style={{ flex: 1 }}>
          <AppButton
            label={confirming ? "Confirming your request…" : "Confirm service request"}
            onPress={onConfirm}
            disabled={!eligibility.allowed || confirming}
            loading={confirming}
            fullWidth
          />
        </View>
      </View>
      <AppText variant="caption" color="tertiary" align="center">No online payment now</AppText>
    </View>
  );
}
