import React from "react";
import { View } from "react-native";
import { useTheme } from "../../../design-system/themes";
import { AppText } from "../../../design-system/components/typography/AppText";
import { Icon } from "../../../design-system/components/Icon";
import { ProfileReadinessDTO } from "../../../services/profile/types";

/** Every number here is backend-calculated (spec section 5) -- never a
 * client-side percentage. */
export function ReadinessStrip({ readiness }: { readiness: ProfileReadinessDTO }) {
  const { theme } = useTheme();
  return (
    <View style={{ flexDirection: "row", gap: theme.spacing.sm }}>
      <View style={{ flex: 1, alignItems: "center" }}>
        <Icon name="person-outline" size="compact" color={theme.colors.textTertiary} decorative />
        <AppText variant="bodyStrong">Profile {readiness.profile_percentage}%</AppText>
      </View>
      <View style={{ flex: 1, alignItems: "center" }}>
        <Icon name="document-text-outline" size="compact" color={theme.colors.textTertiary} decorative />
        <AppText variant="bodyStrong">Documents {readiness.verified_documents}/{readiness.required_documents}</AppText>
      </View>
      <View style={{ flex: 1, alignItems: "center" }}>
        <Icon name="shield-checkmark-outline" size="compact" color={readiness.account_verified ? theme.colors.statusSuccess : theme.colors.textTertiary} decorative />
        <AppText variant="bodyStrong" color={readiness.account_verified ? "success" : "primary"}>{readiness.account_verified ? "Account verified" : "Not verified"}</AppText>
      </View>
    </View>
  );
}
