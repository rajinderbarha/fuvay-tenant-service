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
  const divider = { borderRightWidth: 1, borderRightColor: theme.colors.borderSubtle };
  return (
    <View style={{ flexDirection: "row" }}>
      <View style={[{ flex: 1, alignItems: "center", paddingHorizontal: theme.spacing.sm }, divider]}>
        <Icon name="person-outline" size="compact" color={theme.colors.textTertiary} decorative />
        <AppText variant="bodyStrong">Profile {readiness.profile_percentage}%</AppText>
        <View style={{ width: "100%", height: 3, borderRadius: 2, backgroundColor: theme.colors.borderSubtle, marginTop: theme.spacing.xs, overflow: "hidden" }}>
          <View style={{ width: `${Math.max(0, Math.min(100, readiness.profile_percentage))}%`, height: "100%", backgroundColor: theme.colors.brandPrimary }} />
        </View>
      </View>
      <View style={[{ flex: 1, alignItems: "center", paddingHorizontal: theme.spacing.sm }, divider]}>
        <Icon name="document-text-outline" size="compact" color={theme.colors.textTertiary} decorative />
        <AppText variant="bodyStrong">Documents {readiness.verified_documents}/{readiness.required_documents}</AppText>
      </View>
      <View style={{ flex: 1, alignItems: "center", paddingHorizontal: theme.spacing.sm }}>
        <Icon name="shield-checkmark-outline" size="compact" color={readiness.account_verified ? theme.colors.statusSuccess : theme.colors.textTertiary} decorative />
        <AppText variant="bodyStrong">{readiness.account_verified ? "Account verified" : "Not verified"}</AppText>
      </View>
    </View>
  );
}
