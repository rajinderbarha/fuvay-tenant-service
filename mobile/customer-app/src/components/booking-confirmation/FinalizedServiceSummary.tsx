import React from "react";
import { View } from "react-native";
import { useTheme } from "../../design-system/theme";
import { AppText } from "../AppText";
import { AppCard } from "../AppCard";
import { BookingReceipt } from "../../domain/bookingReceipt";

export function FinalizedServiceSummary({ service }: { service: BookingReceipt["service"] }) {
  const { theme } = useTheme();
  return (
    <AppCard>
      <AppText variant="labelStrong" color="secondary">Booking summary</AppText>
      <View style={{ marginTop: theme.spacing.xxs }}>
        {service.name ? <AppText variant="bodyStrong">{service.name}</AppText> : null}
        {service.jobType ? <AppText variant="bodySmall" color="secondary">{service.jobType}</AppText> : null}
        {service.issueSummary ? <AppText variant="body" style={{ marginTop: theme.spacing.xxs }}>Issue: {service.issueSummary}</AppText> : null}
        {service.answers.map(a => <AppText key={a.key} variant="body">{a.label}: {a.displayValue}</AppText>)}
      </View>
    </AppCard>
  );
}
