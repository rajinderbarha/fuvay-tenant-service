import React from "react";
import { View } from "react-native";
import { useTheme } from "../../design-system/theme";
import { AppText } from "../AppText";
import { AppCard } from "../AppCard";
import { AppBadge } from "../AppBadge";
import { FinalizedPricingPresentation } from "../../domain/bookingReceipt";
import { resolveServicePriceDisplay } from "../../domain/servicePricing";
import { formatMoney } from "../../domain/money";

/** Same zero/Free discipline as the Review phase's PricingReviewCard --
 * never a fabricated number, never ₹0/Free without an explicit backend
 * state (spec section 6). */
export function FinalizedPricingCard({ pricing }: { pricing: FinalizedPricingPresentation }) {
  const { theme } = useTheme();

  if (pricing.inspection) {
    return (
      <AppCard>
        <AppText variant="labelStrong" color="secondary">Visit & payment</AppText>
        <View style={{ flexDirection: "row", justifyContent: "space-between", alignItems: "center", marginTop: theme.spacing.xxs }}>
          <AppText variant="body">Visit fee</AppText>
          <View style={{ flexDirection: "row", alignItems: "center", gap: theme.spacing.xxs }}>
            <AppText variant="bodyStrong">{formatMoney(pricing.inspection.visitFee)}</AppText>
            <AppBadge label="Backend confirmed" tone="success" />
          </View>
        </View>
        <View style={{ flexDirection: "row", justifyContent: "space-between", marginTop: theme.spacing.xxs }}>
          <AppText variant="body" color="secondary">Repair quote</AppText>
          <AppText variant="body">After inspection</AppText>
        </View>
        <View style={{ flexDirection: "row", justifyContent: "space-between" }}>
          <AppText variant="body" color="secondary">Payment</AppText>
          <AppText variant="body">Pay provider directly</AppText>
        </View>
        <AppText variant="caption" color="tertiary" style={{ marginTop: theme.spacing.xs }}>
          No online payment has been collected.
        </AppText>
      </AppCard>
    );
  }

  if (pricing.state.kind === "valid") {
    const display = resolveServicePriceDisplay(pricing.state);
    return (
      <AppCard>
        <AppText variant="labelStrong" color="secondary">Visit & payment</AppText>
        <AppText variant="bodyStrong" style={{ marginTop: theme.spacing.xxs }}>{formatMoney(pricing.state.amount)}</AppText>
        <AppText variant="caption" color="tertiary">{display.label}</AppText>
        <AppText variant="caption" color="tertiary" style={{ marginTop: theme.spacing.xs }}>
          No online payment has been collected.
        </AppText>
      </AppCard>
    );
  }

  return (
    <AppCard>
      <AppText variant="labelStrong" color="secondary">Visit & payment</AppText>
      <AppText variant="bodySmall" color="secondary" style={{ marginTop: theme.spacing.xxs }}>
        Pricing details will be confirmed shortly. Check My Bookings for updates.
      </AppText>
    </AppCard>
  );
}
