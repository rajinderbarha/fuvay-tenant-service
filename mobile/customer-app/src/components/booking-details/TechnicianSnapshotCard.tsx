import React from "react";
import { View, Image } from "react-native";
import { useTheme } from "../../design-system/theme";
import { AppText } from "../AppText";
import { AppCard } from "../AppCard";
import { Icon } from "../Icon";
import { CustomerJobTechnician } from "../../domain/customerBookingDetails";

/** Renders only after a real assignment (`technician` is non-null only
 * when the backend resolved a real `ProviderTeamMember` row). No phone,
 * email, Call or Chat action -- none of those have a proven customer-
 * authorized backend contract on this screen (mission's absolute
 * prohibitions). A neutral fallback avatar is used when no real approved
 * photo exists; missing designation is simply omitted, never guessed. */
export function TechnicianSnapshotCard({ technician }: { technician: CustomerJobTechnician }) {
  const { theme } = useTheme();
  return (
    <AppCard>
      <AppText variant="labelStrong" color="secondary">Assigned professional</AppText>
      <View style={{ flexDirection: "row", alignItems: "center", gap: theme.spacing.sm, marginTop: theme.spacing.xs }}>
        {technician.photoUrl ? (
          <Image
            source={{ uri: technician.photoUrl }}
            accessibilityIgnoresInvertColors
            style={{ width: 44, height: 44, borderRadius: theme.radius.radiusFull, backgroundColor: theme.colors.surfaceInteractive }}
          />
        ) : (
          <View
            style={{
              width: 44, height: 44, borderRadius: theme.radius.radiusFull, alignItems: "center", justifyContent: "center",
              backgroundColor: theme.colors.surfaceInteractive,
            }}
          >
            <Icon name="person-outline" size="standard" color={theme.colors.textSecondary} decorative />
          </View>
        )}
        <View style={{ flex: 1 }}>
          <AppText variant="bodyStrong">{technician.displayName}</AppText>
          {technician.designation ? (
            <AppText variant="bodySmall" color="secondary">{technician.designation}</AppText>
          ) : null}
        </View>
      </View>
    </AppCard>
  );
}
