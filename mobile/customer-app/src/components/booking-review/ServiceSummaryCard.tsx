import React from "react";
import { View } from "react-native";
import { useTheme } from "../../design-system/theme";
import { AppText } from "../AppText";
import { AppCard } from "../AppCard";
import { AppBadge } from "../AppBadge";
import { BookingReviewSummary } from "../../domain/bookingReview";

export interface ServiceSummaryCardProps {
  summary: BookingReviewSummary;
  onEditAnswers: () => void;
}

export function ServiceSummaryCard({ summary, onEditAnswers }: ServiceSummaryCardProps) {
  const { theme } = useTheme();
  return (
    <AppCard style={{ gap: theme.spacing.sm }}>
      <View style={{ flexDirection: "row", justifyContent: "space-between", alignItems: "flex-start" }}>
        <View style={{ flex: 1 }}>
          <AppText variant="bodyStrong">{summary.offeringName}</AppText>
          {summary.inspection ? (
            <AppText variant="bodySmall" color="secondary">Inspection-based service</AppText>
          ) : null}
          {summary.categoryName ? <AppBadge label={summary.categoryName} tone="neutral" /> : null}
        </View>
        {summary.readyForConfirmation ? <AppBadge label="Ready to request" tone="success" /> : null}
      </View>

      <View style={{ borderTopWidth: 1, borderTopColor: theme.colors.borderSubtle, paddingTop: theme.spacing.sm }}>
        <View style={{ flexDirection: "row", justifyContent: "space-between", alignItems: "center" }}>
          <AppText variant="labelStrong" color="secondary">Service details</AppText>
          <AppText variant="labelStrong" color="link" onPress={onEditAnswers}>Edit answers</AppText>
        </View>
        {summary.issueSummary ? (
          <AppText variant="body" style={{ marginTop: theme.spacing.xxs }}>Issue: {summary.issueSummary}</AppText>
        ) : null}
        {summary.jobTypeLabel ? (
          <AppText variant="body">Type: {summary.jobTypeLabel}</AppText>
        ) : null}
        {summary.answers.map(a => (
          <AppText key={a.key} variant="body">{a.label}: {a.value}</AppText>
        ))}
      </View>
    </AppCard>
  );
}
