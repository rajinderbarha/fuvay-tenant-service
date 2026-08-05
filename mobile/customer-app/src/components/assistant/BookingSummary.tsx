import React from "react";
import { View } from "react-native";
import { useTheme } from "../../design-system/theme";
import { AppText } from "../AppText";
import { AppCard } from "../AppCard";
import { Icon, IconProps } from "../Icon";
import { QuestionFlowEnvelope } from "../../domain/questionEnvelope";
import { AssistantEntryContext } from "../../domain/assistantEntry";

export interface BookingSummaryProps {
  entryContext: AssistantEntryContext;
  envelope: QuestionFlowEnvelope | null;
  /** Real, backend-resolved price. Null until every question is answered
   * and the backend has actually returned one -- never fabricated. */
  price?: {
    displayPrice: string | null;
    visitFee: number | null;
    requiresInspectionEstimate: boolean;
    customerMessage: string | null;
  } | null;
}

function SummaryRow({ icon, label, value }: { icon: IconProps["name"]; label: string; value: string }) {
  const { theme } = useTheme();
  return (
    <View style={{ flexDirection: "row", alignItems: "center", gap: theme.spacing.xs, minWidth: "45%" }}>
      <Icon name={icon} size="compact" color={theme.colors.textSecondary} decorative />
      <View>
        <AppText variant="caption" color="tertiary">{label}</AppText>
        <AppText variant="labelStrong">{value}</AppText>
      </View>
    </View>
  );
}

/** question_key -> icon, for the small set of catalog question keys this
 * app's own seed data uses (brand/ac_type/leak_location/etc.) -- falls
 * back to a generic icon for any question_key not in this list, so a
 * newly admin-authored question never breaks the summary, it just shows
 * with a neutral icon. */
function iconForQuestionKey(key: string): IconProps["name"] {
  if (key === "brand") return "pricetag-outline";
  if (key.includes("type")) return "options-outline";
  if (key.includes("size") || key.includes("room")) return "resize-outline";
  return "information-circle-outline";
}

/**
 * Only ever shows fields the backend has actually confirmed. Before a
 * real price exists this NEVER shows ₹0, "Free", a fabricated range, or a
 * Low/Mid/High estimate -- it shows "Price pending" (spec's exact wording),
 * mirroring the same zero-price discipline as domain/servicePricing.ts on
 * Home. Service/Area come from entryContext/zipcode (always known); any
 * further rows (brand, type, etc.) come from envelope.answeredQuestions --
 * real, backend-confirmed answers, never fabricated ahead of the customer
 * actually answering them.
 */
export function BookingSummary({ entryContext, envelope, price }: BookingSummaryProps) {
  const { theme } = useTheme();
  const categoryName = entryContext.source === "service_card" ? entryContext.categoryName : null;
  const progress = envelope?.progress;
  const answered = envelope?.answeredQuestions ?? [];

  return (
    <AppCard>
      <View style={{ flexDirection: "row", alignItems: "center", justifyContent: "space-between" }}>
        <AppText variant="labelStrong" color="secondary">Your booking summary</AppText>
        <View style={{ flexDirection: "row", alignItems: "center", gap: theme.spacing.xxs }}>
          <View style={{ width: 6, height: 6, borderRadius: theme.radius.radiusFull, backgroundColor: theme.colors.statusSuccess }} />
          <AppText variant="caption" color="secondary">Live update</AppText>
        </View>
      </View>
      <View style={{ marginTop: theme.spacing.sm, flexDirection: "row", flexWrap: "wrap", gap: theme.spacing.sm }}>
        {categoryName ? <SummaryRow icon="construct-outline" label="Service" value={categoryName} /> : null}
        <SummaryRow icon="location-outline" label="Area" value={entryContext.zipcode} />
        {answered.map(a => (
          <SummaryRow key={a.questionId} icon={iconForQuestionKey(a.questionKey)} label={a.questionLabel} value={a.answerLabel} />
        ))}
      </View>
      {progress ? (
        <AppText variant="caption" color="tertiary" style={{ marginTop: theme.spacing.xs }}>
          {progress.answeredCount}/{progress.answeredCount + progress.remainingCount} details answered
        </AppText>
      ) : null}
      {/* Real price, resolved by the Assistant itself as soon as every
          question is answered (see useAssistantController's price effect).
          Previously this said "Price pending" forever, because price was
          only ever resolved on Booking Review -- so a customer who had
          answered everything still saw no price on the screen where they
          were actually deciding. Still never fabricates: with no
          backend-resolved price it falls back to the honest pending copy. */}
      <View style={{ marginTop: theme.spacing.sm, paddingTop: theme.spacing.sm, borderTopWidth: 1, borderTopColor: theme.colors.borderSubtle }}>
        {price && (price.displayPrice || price.visitFee != null) ? (
          <>
            <View style={{ flexDirection: "row", alignItems: "center", gap: theme.spacing.xxs }}>
              <AppText variant="bodyStrong">
                {price.displayPrice ?? `Rs.${price.visitFee}`}
              </AppText>
              {price.requiresInspectionEstimate ? (
                <AppText variant="caption" color="secondary">visit fee</AppText>
              ) : null}
            </View>
            <AppText variant="caption" color="tertiary">
              {price.customerMessage
                ?? (price.requiresInspectionEstimate
                  ? "The technician will inspect and share an estimate before any repair."
                  : "Final price confirmed at review.")}
            </AppText>
            {/* The visit fee is NOT an extra charge -- it comes off the final
                bill if the customer goes ahead. Highlighted (brand tint,
                own chip) rather than buried in the grey caption above,
                because it is the single line that makes an inspection-first
                price feel fair instead of like a surprise call-out fee. */}
            {price.requiresInspectionEstimate ? (
              <View style={{
                marginTop: theme.spacing.xs,
                paddingHorizontal: theme.spacing.sm, paddingVertical: theme.spacing.xs,
                borderRadius: theme.radiusUsage.input,
                backgroundColor: theme.colors.brandPrimaryMuted,
                flexDirection: "row", alignItems: "center", gap: theme.spacing.xxs,
              }}>
                <Icon name="checkmark-circle" size="compact" color={theme.colors.brandPrimaryStrong} decorative />
                <AppText variant="caption" style={{ color: theme.colors.brandPrimaryStrong, flex: 1 }}>
                  This visit fee is adjusted against your final bill if you continue with the service.
                </AppText>
              </View>
            ) : null}
          </>
        ) : (
          <>
            <View style={{ flexDirection: "row", alignItems: "center", gap: theme.spacing.xxs }}>
              <AppText variant="bodyStrong">Price pending</AppText>
              <Icon name="information-circle-outline" size="compact" color={theme.colors.textTertiary} decorative />
            </View>
            <AppText variant="caption" color="tertiary">
              {progress?.complete
                ? "Checking your price and provider..."
                : "Complete required details to check availability"}
            </AppText>
          </>
        )}
      </View>
    </AppCard>
  );
}
