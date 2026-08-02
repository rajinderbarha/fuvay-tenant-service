import React from "react";
import { View } from "react-native";
import { useTheme } from "../../../design-system/themes";
import { AppText } from "../../../design-system/components/typography/AppText";
import { Icon } from "../../../design-system/components/Icon";
import { Money } from "../../../design-system/components/data-display/Money";
import { ApprovedScopeDTO } from "../../../services/workExecution/types";

/** Read-only -- approved scope can never be edited from this screen
 * (spec section 13: labour rate, parts, visit fee, tax, total, terms are
 * all locked by the canonical quote engine's own immutability guard). */
export function ApprovedScopeBanner({ scope, onView }: { scope: ApprovedScopeDTO; onView: () => void }) {
  const { theme } = useTheme();
  return (
    <View
      accessibilityRole="button"
      onTouchEnd={onView}
      style={{
        flexDirection: "row", alignItems: "center", gap: theme.spacing.sm, padding: theme.spacing.base,
        borderRadius: theme.radiusUsage.card, backgroundColor: theme.colors.statusSuccessSurface,
      }}
    >
      <Icon name="checkmark-circle" size="standard" color={theme.colors.statusSuccess} decorative />
      <View style={{ flex: 1 }}>
        <AppText variant="bodyStrong" style={{ color: theme.colors.statusSuccess }}>Estimate v{scope.version_number} approved</AppText>
        <View style={{ flexDirection: "row", alignItems: "center", gap: 4 }}>
          <AppText variant="caption" style={{ color: theme.colors.statusSuccess }}>Approved total </AppText>
          <Money amount={Number(scope.approved_total)} size="medium" style={{ color: theme.colors.statusSuccess }} />
          <AppText variant="caption" style={{ color: theme.colors.statusSuccess }}> · Scope locked</AppText>
        </View>
      </View>
    </View>
  );
}
