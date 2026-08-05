import React from "react";
import { View } from "react-native";
import { useTheme } from "../../design-system/theme";
import { AppText } from "../AppText";
import { AppCard } from "../AppCard";
import { AppBadge } from "../AppBadge";
import { Icon } from "../Icon";
import { ReviewProvider } from "../../domain/bookingReview";

export interface ProviderAssignmentCardProps {
  provider: ReviewProvider | null;
}

/**
 * Never a provider list, never a selection control (spec section 4). Only
 * shows trust chips the backend's own `public_badges` actually carry --
 * never a fabricated "Verified"/"Eligible" chip.
 */
export function ProviderAssignmentCard({ provider }: ProviderAssignmentCardProps) {
  const { theme } = useTheme();
  return (
    <AppCard>
      <View style={{ flexDirection: "row", gap: theme.spacing.sm, alignItems: "flex-start" }}>
        <View
          style={{
            width: 40, height: 40, borderRadius: theme.radius.radiusFull,
            backgroundColor: theme.colors.surfaceInteractive, alignItems: "center", justifyContent: "center",
          }}
        >
          <Icon name="shield-checkmark-outline" size="standard" color={theme.colors.brandPrimaryStrong} decorative />
        </View>
        <View style={{ flex: 1 }}>
          <AppText variant="bodyStrong">Provider assignment</AppText>
          <AppText variant="bodySmall" color="secondary">Fuvay assigns the best eligible professional</AppText>
          <AppText variant="caption" color="tertiary" style={{ marginTop: theme.spacing.xxs }}>
            Based on service availability, coverage and provider readiness.
          </AppText>
          {provider && provider.publicBadges.length > 0 ? (
            <View style={{ flexDirection: "row", flexWrap: "wrap", gap: theme.spacing.xxs, marginTop: theme.spacing.sm }}>
              {provider.publicBadges.map(badge => <AppBadge key={badge.name} label={badge.name} tone="success" />)}
            </View>
          ) : null}
        </View>
      </View>
    </AppCard>
  );
}
