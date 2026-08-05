import React from "react";
import { View } from "react-native";
import { useTheme } from "../../design-system/theme";
import { AppText } from "../AppText";
import { AppBadge } from "../AppBadge";
import { Icon } from "../Icon";
import { maskPhoneForDisplay } from "../../domain/phone";

export interface MobileNumberRowProps {
  phone: string | null;
  /** Only ever the real backend `is_verified` flag -- never derived from
   * the mere presence of a phone number (spec section 5). No `Change`
   * action: no authenticated contact-change OTP flow exists in this
   * codebase (confirmed via direct audit of `app/engines/auth/router.py`). */
  verified: boolean;
}

export function MobileNumberRow({ phone, verified }: MobileNumberRowProps) {
  const { theme } = useTheme();
  return (
    <View style={{ flexDirection: "row", alignItems: "center", gap: theme.spacing.sm, paddingVertical: theme.spacing.xs }}>
      <View style={{ width: 36, alignItems: "center" }}>
        <Icon name="phone-portrait-outline" size="standard" color={theme.colors.textSecondary} decorative />
      </View>
      <View style={{ flex: 1 }}>
        <AppText variant="bodyStrong">Mobile number</AppText>
        <AppText variant="bodySmall" color="secondary">{phone ? maskPhoneForDisplay(phone) : "Not set"}</AppText>
      </View>
      {verified ? <AppBadge label="Verified" tone="success" /> : null}
    </View>
  );
}
