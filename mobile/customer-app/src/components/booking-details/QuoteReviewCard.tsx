import React, { useState } from "react";
import { View } from "react-native";
import { useTheme } from "../../design-system/theme";
import { AppText } from "../AppText";
import { AppCard } from "../AppCard";
import { AppButton } from "../AppButton";
import { AppInput } from "../AppInput";
import { AppBadge } from "../AppBadge";
import { Icon } from "../Icon";
import { CustomerQuote } from "../../domain/customerQuote";
import { QuoteDecisionStage, resolveQuoteDecisionPresentation } from "../../domain/inspectionQuotePresentation";

export interface QuoteReviewCardProps {
  quote: CustomerQuote;
  decisionStage: QuoteDecisionStage;
  onApprove: () => void;
  onDecline: (reason: string) => void;
  approving: boolean;
  declining: boolean;
}

/** Mission's "Review estimate" + "Your decision" sections, extended in the
 * existing `BookingDetailsScreen` (spec: no second Quote Approval route).
 * Every amount and line item comes from `quote` (already backend-computed
 * and customer-safe filtered server-side) -- this component never sums,
 * discounts, or otherwise recomputes a total itself. Approve/Decline only
 * render when `decisionStage === "ready"`; every other stage shows a
 * read-only outcome, never live decision controls against an unproven or
 * already-decided quote. */
export function QuoteReviewCard({ quote, decisionStage, onApprove, onDecline, approving, declining }: QuoteReviewCardProps) {
  const { theme } = useTheme();
  const [decliningOpen, setDecliningOpen] = useState(false);
  const [reason, setReason] = useState("");
  const presentation = resolveQuoteDecisionPresentation(decisionStage);
  const actionable = decisionStage === "ready";
  const busy = approving || declining;

  return (
    <View style={{ gap: theme.spacing.base }}>
      <AppCard style={{ borderColor: theme.colors.brandPrimary, borderWidth: 1 }}>
        <View style={{ flexDirection: "row", gap: theme.spacing.sm, alignItems: "flex-start" }}>
          <View
            style={{
              width: 44, height: 44, borderRadius: theme.radiusUsage.card, alignItems: "center", justifyContent: "center",
              backgroundColor: theme.colors.brandPrimaryMuted,
            }}
          >
            <Icon name="clipboard-outline" size="standard" color={theme.colors.brandPrimaryStrong} decorative />
          </View>
          <View style={{ flex: 1, gap: theme.spacing.xxs }}>
            <AppText variant="bodyStrong" accessibilityRole="header">{presentation.title}</AppText>
            {presentation.explanation ? <AppText variant="bodySmall" color="secondary">{presentation.explanation}</AppText> : null}
          </View>
        </View>
      </AppCard>

      {quote.findingSummary ? (
        <View style={{ gap: theme.spacing.xs }}>
          <AppText variant="labelStrong" color="secondary">What was found</AppText>
          <AppCard>
            <AppText variant="body">{quote.findingSummary}</AppText>
          </AppCard>
        </View>
      ) : null}

      <View style={{ gap: theme.spacing.xs }}>
        <AppText variant="labelStrong" color="secondary">Review estimate</AppText>
        <AppCard style={{ gap: 0 }}>
          {quote.items.map((item, i) => (
            <View
              key={item.id}
              style={{
                flexDirection: "row", justifyContent: "space-between", paddingVertical: theme.spacing.xs,
                borderBottomWidth: 1, borderBottomColor: theme.colors.borderSubtle,
              }}
            >
              <AppText variant="body" color="secondary" style={{ flex: 1 }}>{item.label}</AppText>
              <AppText variant="body" accessibilityLabel={`${item.label}: ${quote.currency} ${item.lineTotal}`}>
                {quote.currency} {item.lineTotal}
              </AppText>
            </View>
          ))}
          <View style={{ flexDirection: "row", justifyContent: "space-between", paddingTop: theme.spacing.sm }}>
            <AppText variant="bodyStrong">Estimated total</AppText>
            <AppText
              variant="bodyStrong"
              style={{ color: theme.colors.brandPrimaryStrong }}
              accessibilityLabel={`Estimated total: ${quote.currency} ${quote.customerPayableAmount}`}
            >
              {quote.currency} {quote.customerPayableAmount}
            </AppText>
          </View>
        </AppCard>
      </View>

      <View
        style={{
          flexDirection: "row", gap: theme.spacing.sm, alignItems: "flex-start", padding: theme.spacing.sm,
          borderRadius: theme.radiusUsage.card, backgroundColor: theme.colors.surfaceInteractive,
        }}
      >
        <Icon name="shield-checkmark-outline" size="standard" color={theme.colors.textSecondary} decorative />
        <AppText variant="bodySmall" color="secondary" style={{ flex: 1 }}>
          Pay the provider directly after service. Fuvay does not collect job payment.
        </AppText>
      </View>

      {actionable ? (
        <View style={{ gap: theme.spacing.sm }}>
          <AppText variant="labelStrong" color="secondary">Your decision</AppText>
          <AppText variant="bodySmall" color="secondary">Approve to allow repair work to begin.</AppText>
          {!decliningOpen ? (
            <>
              <AppButton
                label={approving ? "Submitting your approval…" : `Approve quote · ${quote.currency} ${quote.customerPayableAmount}`}
                tone="primary" fullWidth disabled={busy} onPress={onApprove}
              />
              <AppButton label="Decline quote" tone="secondary" fullWidth disabled={busy} onPress={() => setDecliningOpen(true)} />
            </>
          ) : (
            <View style={{ gap: theme.spacing.sm }}>
              <AppInput
                label="Why are you declining?" value={reason} onChangeText={setReason}
                multiline placeholder="Tell us why this estimate doesn't work for you"
              />
              <AppButton
                label={declining ? "Submitting your decision…" : "Confirm decline"}
                tone="destructive" fullWidth disabled={busy || !reason.trim()}
                onPress={() => onDecline(reason.trim())}
              />
              <AppButton label="Back" tone="secondary" fullWidth disabled={busy} onPress={() => setDecliningOpen(false)} />
            </View>
          )}
        </View>
      ) : decisionStage === "declined" && quote.rejectionReason ? (
        <View style={{ gap: theme.spacing.xxs }}>
          <AppText variant="labelStrong" color="secondary">Your reason</AppText>
          <AppText variant="bodySmall">{quote.rejectionReason}</AppText>
        </View>
      ) : null}
    </View>
  );
}
