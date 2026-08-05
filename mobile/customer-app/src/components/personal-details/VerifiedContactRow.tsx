import React from "react";
import { View } from "react-native";
import { useTheme } from "../../design-system/theme";
import { AppText } from "../AppText";
import { AppBadge } from "../AppBadge";
import { Icon, IconProps } from "../Icon";

export interface VerifiedContactRowProps {
  icon: IconProps["name"];
  label: string;
  value: string | null;
  verified: boolean;
  helperText: string;
}

/** Read-only by design -- no `Change` action exists because no complete
 * canonical OTP contact-change flow was confirmed this phase (spec
 * section 5: "If this full flow is absent, hide Change and keep the row
 * read-only"). Announces as read-only for screen readers. */
export function VerifiedContactRow({ icon, label, value, verified, helperText }: VerifiedContactRowProps) {
  const { theme } = useTheme();
  if (!value) return null;
  return (
    <View
      accessible
      accessibilityLabel={`${label}: ${value}${verified ? ", verified" : ""}. Read only.`}
      style={{ paddingVertical: theme.spacing.sm, gap: theme.spacing.xxs }}
    >
      <View style={{ flexDirection: "row", alignItems: "center", gap: theme.spacing.sm }}>
        <Icon name={icon} size="standard" color={theme.colors.textSecondary} decorative />
        <View style={{ flex: 1 }}>
          <AppText variant="caption" color="tertiary">{label}</AppText>
          <View style={{ flexDirection: "row", alignItems: "center", gap: theme.spacing.xs }}>
            <AppText variant="body">{value}</AppText>
            {verified ? <AppBadge label="Verified" tone="success" /> : null}
          </View>
        </View>
        <Icon name="lock-closed-outline" size="compact" color={theme.colors.iconDefault} decorative />
      </View>
      <AppText variant="caption" color="tertiary">{helperText}</AppText>
    </View>
  );
}
