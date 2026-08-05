import React from "react";
import { View, Pressable } from "react-native";
import { useTheme } from "../../design-system/theme";
import { AppText } from "../AppText";
import { Icon } from "../Icon";

export interface DefaultAddressToggleProps {
  checked: boolean;
  /** True when the backend will force this address to be default
   * regardless of the toggle (the customer's first address, or the
   * address currently holding default status while editing) -- the
   * control is shown checked and disabled rather than implying an
   * un-default action this form doesn't support (spec section 6). */
  forced: boolean;
  forcedReason?: string;
  onChange: (value: boolean) => void;
}

export function DefaultAddressToggle({ checked, forced, forcedReason, onChange }: DefaultAddressToggleProps) {
  const { theme } = useTheme();
  const isChecked = forced || checked;
  return (
    <View>
      <Pressable
        onPress={() => { if (!forced) onChange(!checked); }}
        disabled={forced}
        accessibilityRole="checkbox"
        accessibilityState={{ checked: isChecked, disabled: forced }}
        accessibilityLabel="Make this my default address"
        hitSlop={4}
        style={{ flexDirection: "row", alignItems: "center", gap: theme.spacing.sm, minHeight: theme.touchTargets.minimum }}
      >
        <View style={{
          width: 22, height: 22, borderRadius: theme.radius.radiusSmall, borderWidth: isChecked ? 0 : 1,
          borderColor: theme.colors.borderDefault, backgroundColor: isChecked ? theme.colors.brandPrimary : theme.colors.surfaceDefault,
          alignItems: "center", justifyContent: "center", opacity: forced ? theme.opacity.disabled : 1,
        }}>
          {isChecked ? <Icon name="checkmark" size="compact" color={theme.colors.brandOnPrimary} decorative /> : null}
        </View>
        <AppText variant="body">Make this my default address</AppText>
      </Pressable>
      {forced && forcedReason ? (
        <AppText variant="caption" color="tertiary" style={{ marginTop: theme.spacing.xxs, marginLeft: 34 }}>
          {forcedReason}
        </AppText>
      ) : null}
    </View>
  );
}
