import React from "react";
import { View } from "react-native";
import { useTheme } from "../../design-system/theme";
import { AppText } from "../AppText";
import { AppCard } from "../AppCard";
import { Icon } from "../Icon";
import { VerifiedContactRow } from "./VerifiedContactRow";

export interface ContactInformationCardProps {
  maskedPhone: string | null;
  email: string | null;
  verified: boolean;
}

export function ContactInformationCard({ maskedPhone, email, verified }: ContactInformationCardProps) {
  const { theme } = useTheme();
  return (
    <AppCard style={{ gap: 0 }}>
      <AppText variant="bodyStrong">Contact information</AppText>
      <VerifiedContactRow
        icon="call-outline" label="Mobile number" value={maskedPhone} verified={verified}
        helperText="Changing your mobile requires OTP verification."
      />
      <VerifiedContactRow
        icon="mail-outline" label="Email address" value={email} verified={verified}
        helperText="Changing your email requires verification."
      />
      <View
        style={{
          flexDirection: "row", gap: theme.spacing.sm, alignItems: "flex-start",
          marginTop: theme.spacing.sm, padding: theme.spacing.sm,
          backgroundColor: theme.colors.statusSuccessSurface, borderRadius: theme.radiusUsage.input,
        }}
      >
        <Icon name="shield-checkmark" size="standard" color={theme.colors.statusSuccess} decorative />
        <View style={{ flex: 1 }}>
          <AppText variant="bodyStrong" style={{ color: theme.colors.statusSuccess }}>Your verified details stay protected</AppText>
          <AppText variant="caption" color="secondary">We'll ask you to verify any new mobile number or email address.</AppText>
        </View>
      </View>
    </AppCard>
  );
}
