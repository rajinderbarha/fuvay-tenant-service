import React from "react";
import { View, Image } from "react-native";
import { useTheme } from "../../design-system/theme";
import { AppText } from "../AppText";
import { AppIconButton } from "../AppIconButton";
import { Icon } from "../Icon";

export interface CustomerHeaderProps {
  greeting: string;
  customerFirstName: string;
  avatarUrl?: string | null;
  /** City/ZIP display line -- null means "no address on file", handled
   * by the caller rendering NoAddressState instead of this header's
   * location row (spec: "If the customer has no address, show 'Choose
   * your location.'"). */
  locationLabel: string | null;
  onPressLocation: () => void;
  /** Undefined = not yet checked (nothing rendered), never a guessed
   * default -- "Do not show Serviceable until the backend confirms it." */
  serviceable?: boolean;
  unreadNotifications: boolean;
  onPressAvatar?: () => void;
  onPressNotifications: () => void;
}

/** No Fuvay logo/wordmark on this screen (spec requirement) -- identity
 * here is the customer's own greeting + avatar. */
export function CustomerHeader({
  greeting, customerFirstName, avatarUrl, locationLabel, onPressLocation, serviceable,
  unreadNotifications, onPressAvatar, onPressNotifications,
}: CustomerHeaderProps) {
  const { theme } = useTheme();
  return (
    <View>
      <View style={{ flexDirection: "row", alignItems: "flex-start", justifyContent: "space-between" }}>
        <View style={{ flex: 1 }}>
          <AppText variant="headingSmall" accessibilityRole="header">
            {`${greeting} ${customerFirstName}`}
          </AppText>
          <View
            accessible
            accessibilityRole="button"
            accessibilityLabel={locationLabel ? `Location: ${locationLabel}${serviceable ? ", serviceable" : ""}` : "Choose your location"}
            onTouchEnd={onPressLocation}
            style={{ flexDirection: "row", alignItems: "center", gap: theme.spacing.xxs, marginTop: theme.spacing.xxs, flexWrap: "wrap" }}
          >
            <Icon name="location-outline" size="compact" color={theme.colors.iconDefault} decorative />
            <AppText variant="bodySmall" color="secondary">{locationLabel ?? "Choose your location"}</AppText>
            {serviceable === true ? (
              <View style={{ flexDirection: "row", alignItems: "center", gap: 4, marginLeft: theme.spacing.xs }}>
                <View style={{ width: 6, height: 6, borderRadius: theme.radius.radiusFull, backgroundColor: theme.colors.statusSuccess }} accessibilityElementsHidden />
                <AppText variant="caption" style={{ color: theme.colors.statusSuccess }}>Serviceable</AppText>
              </View>
            ) : null}
          </View>
        </View>
        <View style={{ flexDirection: "row", alignItems: "center", gap: theme.spacing.sm }}>
          <View style={{ position: "relative" }}>
            <AppIconButton name="notifications-outline" accessibilityLabel={unreadNotifications ? "Notifications, unread" : "Notifications"} onPress={onPressNotifications} />
            {unreadNotifications ? (
              <View
                accessibilityElementsHidden
                style={{ position: "absolute", top: 4, right: 4, width: 8, height: 8, borderRadius: theme.radius.radiusFull, backgroundColor: theme.colors.statusDanger }}
              />
            ) : null}
          </View>
          <View
            accessible
            accessibilityRole={onPressAvatar ? "button" : "image"}
            accessibilityLabel={`${customerFirstName}'s profile photo`}
            onTouchEnd={onPressAvatar}
            style={{
              width: 40, height: 40, borderRadius: theme.radius.radiusFull, overflow: "hidden",
              backgroundColor: theme.colors.surfaceInteractive, alignItems: "center", justifyContent: "center",
              borderWidth: 1, borderColor: theme.colors.borderSubtle,
            }}
          >
            {avatarUrl ? (
              <Image source={{ uri: avatarUrl }} style={{ width: "100%", height: "100%" }} />
            ) : (
              <AppText variant="bodyStrong" color="secondary">{customerFirstName.charAt(0).toUpperCase()}</AppText>
            )}
          </View>
        </View>
      </View>
    </View>
  );
}
