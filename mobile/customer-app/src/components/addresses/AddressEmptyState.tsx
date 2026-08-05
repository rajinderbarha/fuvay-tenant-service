import React from "react";
import { View } from "react-native";
import { useTheme } from "../../design-system/theme";
import { AppText } from "../AppText";
import { AppButton } from "../AppButton";
import { Icon } from "../Icon";

export interface AddressEmptyStateProps {
  onAddAddress?: () => void;
}

/** No sample Work/Family addresses -- honest empty state only (spec
 * section 5: "Do not create sample Work/Family addresses"). `Add address`
 * renders only when `onAddAddress` is supplied (functional form exists). */
export function AddressEmptyState({ onAddAddress }: AddressEmptyStateProps) {
  const { theme } = useTheme();
  return (
    <View
      style={{
        alignItems: "center", gap: theme.spacing.xs, padding: theme.spacing.base,
        borderWidth: 1, borderStyle: "dashed", borderColor: theme.colors.borderDefault,
        borderRadius: theme.radiusUsage.card,
      }}
    >
      <Icon name="location-outline" size="feature" color={theme.colors.textTertiary} decorative />
      <AppText variant="bodyStrong">No other saved addresses</AppText>
      <AppText variant="bodySmall" color="secondary" align="center">Add another address for home, work or family.</AppText>
      {onAddAddress ? (
        <AppButton label="Add address" tone="secondary" onPress={onAddAddress} />
      ) : null}
    </View>
  );
}
