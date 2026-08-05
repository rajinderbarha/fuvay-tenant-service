import React from "react";
import { View, Image } from "react-native";
import { useTheme } from "../../design-system/theme";
import { AppText } from "../AppText";
import { AppCard } from "../AppCard";
import { AppBadge } from "../AppBadge";
import { AppButton } from "../AppButton";
import { CustomerProfile } from "../../domain/customer";

export interface CustomerIdentityCardProps {
  profile: CustomerProfile;
  onEditProfile?: () => void;
}

/** Renders only real backend fields -- no fabricated name/contact data,
 * no split mobile/email verified badges (the backend has one combined
 * `is_verified` flag, see domain/customer.ts). Camera badge is entirely
 * absent since avatar upload isn't a proven capability this phase. */
export function CustomerIdentityCard({ profile, onEditProfile }: CustomerIdentityCardProps) {
  const { theme } = useTheme();
  const name = profile.displayName ?? profile.fullName ?? "Your account";
  const initial = name.trim().charAt(0).toUpperCase() || "?";

  return (
    <AppCard style={{ gap: theme.spacing.sm }}>
      <View style={{ flexDirection: "row", gap: theme.spacing.sm, alignItems: "center" }}>
        <View
          accessibilityRole="image"
          accessibilityLabel={`${name}'s profile photo`}
          style={{
            width: 64, height: 64, borderRadius: theme.radius.radiusFull, overflow: "hidden",
            backgroundColor: theme.colors.surfaceInteractive, alignItems: "center", justifyContent: "center",
            borderWidth: 1, borderColor: theme.colors.borderSubtle,
          }}
        >
          {profile.avatarUrl ? (
            <Image source={{ uri: profile.avatarUrl }} style={{ width: "100%", height: "100%" }} />
          ) : (
            <AppText variant="title" color="secondary">{initial}</AppText>
          )}
        </View>
        <View style={{ flex: 1, gap: theme.spacing.xxs }}>
          <AppText variant="bodyStrong">{name}</AppText>
          {profile.phone ? <AppText variant="bodySmall" color="secondary">{profile.phone}</AppText> : null}
          {profile.email ? <AppText variant="bodySmall" color="secondary">{profile.email}</AppText> : null}
          {profile.verified ? (
            <View style={{ flexDirection: "row", gap: theme.spacing.xxs, marginTop: theme.spacing.xxs }}>
              <AppBadge label="Verified" tone="success" />
            </View>
          ) : null}
        </View>
      </View>
      {onEditProfile ? <AppButton label="Edit profile" tone="secondary" onPress={onEditProfile} fullWidth /> : null}
    </AppCard>
  );
}
