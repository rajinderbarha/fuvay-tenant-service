import React from "react";
import { View, Image } from "react-native";
import { useTheme } from "../../../design-system/themes";
import { Card } from "../../../design-system/components/foundation/Layout";
import { AppText } from "../../../design-system/components/typography/AppText";
import { SecondaryButton } from "../../../design-system/components/actions/Buttons";
import { ProfileIdentityDTO, ProfileEmploymentDTO } from "../../../services/profile/types";

/** Every field here is backend-projected -- role/business/status are
 * tenant-controlled and shown read-only (spec section 4). */
export function IdentityCard({ identity, employment, onEdit }: { identity: ProfileIdentityDTO; employment: ProfileEmploymentDTO; onEdit: () => void }) {
  const { theme } = useTheme();
  return (
    <Card style={{ flexDirection: "row", alignItems: "flex-start", gap: theme.spacing.base }}>
      <View style={{ width: 64, height: 64, borderRadius: 32, overflow: "hidden", backgroundColor: theme.colors.surfaceInteractive, alignItems: "center", justifyContent: "center" }}>
        {identity.photo_url ? (
          <Image source={{ uri: identity.photo_url }} style={{ width: 64, height: 64 }} />
        ) : (
          <AppText variant="title">{identity.full_name.charAt(0)}</AppText>
        )}
      </View>
      <View style={{ flex: 1 }}>
        <AppText variant="title">{identity.full_name}</AppText>
        {employment.designation ? <AppText color="secondary">{employment.designation}</AppText> : null}
        {employment.business_name ? <AppText color="secondary">{employment.business_name}</AppText> : null}
        {identity.masked_mobile ? <AppText color="tertiary">{identity.masked_mobile}</AppText> : null}
        <View style={{ flexDirection: "row", alignItems: "center", marginTop: theme.spacing.xs, gap: theme.spacing.sm }}>
          <View style={{ flexDirection: "row", alignItems: "center", gap: 4, paddingHorizontal: theme.spacing.sm, paddingVertical: 2, borderRadius: theme.radiusUsage.statusPill, backgroundColor: identity.status === "active" ? theme.colors.statusSuccessSurface : theme.colors.statusNeutralSurface }}>
            <View style={{ width: 6, height: 6, borderRadius: 3, backgroundColor: identity.status === "active" ? theme.colors.statusSuccess : theme.colors.textTertiary }} />
            <AppText variant="caption" color={identity.status === "active" ? "success" : "tertiary"}>{identity.status === "active" ? "Active" : identity.status}</AppText>
          </View>
          <SecondaryButton label="Edit profile" onPress={onEdit} />
        </View>
      </View>
    </Card>
  );
}
