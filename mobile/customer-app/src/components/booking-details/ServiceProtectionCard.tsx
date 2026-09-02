import React from "react";
import { View } from "react-native";
import { AppButton } from "../AppButton";
import { AppCard } from "../AppCard";
import { AppText } from "../AppText";
import { useTheme } from "../../design-system/theme";

interface Props {
  warrantyDays: number | null;
  warrantyExpiresAt: string | null;
  warrantyActive: boolean;
  certificateNumber?: string | null;
  onDownloadWarranty?: () => void;
  onClaimWarranty: () => void;
  onRequestRefund: () => void;
}

export function ServiceProtectionCard({
  warrantyDays, warrantyExpiresAt, warrantyActive, certificateNumber,
  onDownloadWarranty, onClaimWarranty, onRequestRefund,
}: Props) {
  const { theme } = useTheme();
  const expiry = warrantyExpiresAt ? new Date(warrantyExpiresAt).toLocaleDateString() : null;
  return (
    <AppCard style={{ gap: theme.spacing.sm }}>
      <View style={{ gap: theme.spacing.xxs }}>
        <AppText variant="bodyStrong">Service protection</AppText>
        <AppText variant="bodySmall" color="secondary">
          {warrantyActive
            ? `${warrantyDays ?? 5}-day provider warranty${expiry ? ` · valid until ${expiry}` : ""}`
            : "The provider warranty period has ended."}
        </AppText>
        <AppText variant="caption" color="tertiary">
          Your provider is responsible for inspection and resolution. Rework, refund, credit, or another settlement requires your agreement with the provider.
        </AppText>
      </View>
      {warrantyActive && certificateNumber ? (
        <AppButton label={`Download warranty · ${certificateNumber}`} tone="secondary" onPress={onDownloadWarranty!} fullWidth />
      ) : null}
      {warrantyActive ? <AppButton label="Claim warranty" onPress={onClaimWarranty} fullWidth /> : null}
      <AppButton label="Request refund" tone="secondary" onPress={onRequestRefund} fullWidth />
    </AppCard>
  );
}
