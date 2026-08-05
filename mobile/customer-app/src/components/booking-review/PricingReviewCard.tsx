import React from "react";
import { View } from "react-native";
import { useTheme } from "../../design-system/theme";
import { AppText } from "../AppText";
import { AppCard } from "../AppCard";
import { AppBadge } from "../AppBadge";
import { Icon } from "../Icon";
import { ServicePriceState, InspectionPricing, resolveServicePriceDisplay } from "../../domain/servicePricing";
import { formatMoney } from "../../domain/money";

export interface PricingReviewCardProps {
  priceState: ServicePriceState;
  inspection: InspectionPricing | null;
  bargainAvailable: boolean;
}

/**
 * Never renders ₹0/Free for a non-explicit-free state (spec section 5) --
 * every branch here maps 1:1 to a `ServicePriceState.kind`, no numeric
 * fallback is ever synthesized.
 */
export function PricingReviewCard({ priceState, inspection, bargainAvailable }: PricingReviewCardProps) {
  const { theme } = useTheme();

  if (inspection) {
    return (
      <AppCard style={{ backgroundColor: theme.colors.brandPrimaryMuted, borderColor: theme.colors.brandPrimary }}>
        <AppText variant="labelStrong" style={{ color: theme.colors.brandPrimaryStrong }}>Inspection required</AppText>
        <View style={{ flexDirection: "row", alignItems: "center", gap: theme.spacing.xs, marginTop: theme.spacing.xxs }}>
          <AppText variant="title">{formatMoney(inspection.visitFee)} visit fee</AppText>
          <AppBadge label="Backend confirmed" tone="success" />
        </View>
        <AppText variant="bodySmall" color="secondary" style={{ marginTop: theme.spacing.xxs }}>
          The technician will inspect your service and provide an estimate before starting the work.
        </AppText>
        <AppText variant="bodySmall" color="secondary" style={{ marginTop: theme.spacing.xxs }}>
          Your approval will be required before repair begins.
        </AppText>
        <View style={{ marginTop: theme.spacing.sm, gap: theme.spacing.xxs }}>
          <View style={{ flexDirection: "row", justifyContent: "space-between" }}>
            <AppText variant="body" color="secondary">Repair price</AppText>
            <AppText variant="body">After inspection</AppText>
          </View>
          <View style={{ flexDirection: "row", justifyContent: "space-between" }}>
            <AppText variant="body" color="secondary">Payment</AppText>
            <AppText variant="body">Pay provider directly</AppText>
          </View>
        </View>
        {inspection.feeAdjustmentNote ? (
          <View style={{ flexDirection: "row", gap: theme.spacing.xxs, marginTop: theme.spacing.sm }}>
            <Icon name="information-circle-outline" size="compact" color={theme.colors.textTertiary} decorative />
            <AppText variant="caption" color="tertiary" style={{ flex: 1 }}>{inspection.feeAdjustmentNote}</AppText>
          </View>
        ) : null}
      </AppCard>
    );
  }

  if (priceState.kind === "valid") {
    const display = resolveServicePriceDisplay(priceState);
    return (
      <AppCard>
        <AppText variant="labelStrong" color="secondary">Price</AppText>
        <AppText variant="title" style={{ marginTop: theme.spacing.xxs }}>{formatMoney(priceState.amount)}</AppText>
        <AppText variant="caption" color="tertiary">{display.label}</AppText>
      </AppCard>
    );
  }

  if (bargainAvailable || priceState.kind === "quote_required") {
    return (
      <AppCard>
        <AppText variant="bodyStrong">Price selection coming soon</AppText>
        <AppText variant="bodySmall" color="secondary" style={{ marginTop: theme.spacing.xxs }}>
          This service supports flexible pricing that isn't available in the app yet.
        </AppText>
      </AppCard>
    );
  }

  return (
    <AppCard>
      <AppText variant="bodyStrong">Pricing is currently unavailable for this service</AppText>
      <AppText variant="bodySmall" color="secondary" style={{ marginTop: theme.spacing.xxs }}>
        We couldn't confirm a valid price for this request right now.
      </AppText>
    </AppCard>
  );
}
