import React from "react";
import { View, Pressable } from "react-native";
import { useTheme } from "../../design-system/theme";
import { AppText } from "../AppText";
import { Icon } from "../Icon";

export interface AcknowledgementCheckboxProps {
  checked: boolean;
  onChange: (value: boolean) => void;
  label: string;
}

/** Purely a local, session-scoped acknowledgement (spec section 6) --
 * never persisted, never sent to the backend as identity verification,
 * never a substitute for real verification. */
export function AcknowledgementCheckbox({ checked, onChange, label }: AcknowledgementCheckboxProps) {
  const { theme } = useTheme();
  return (
    <Pressable
      onPress={() => onChange(!checked)}
      accessibilityRole="checkbox"
      accessibilityState={{ checked }}
      accessibilityLabel={label}
      hitSlop={4}
      style={{ flexDirection: "row", alignItems: "center", gap: theme.spacing.sm, minHeight: theme.touchTargets.minimum }}
    >
      <View style={{
        width: 22, height: 22, borderRadius: theme.radius.radiusSmall, borderWidth: checked ? 0 : 1,
        borderColor: theme.colors.borderDefault, backgroundColor: checked ? theme.colors.brandPrimary : theme.colors.surfaceDefault,
        alignItems: "center", justifyContent: "center",
      }}>
        {checked ? <Icon name="checkmark" size="compact" color={theme.colors.brandOnPrimary} decorative /> : null}
      </View>
      <AppText variant="body" style={{ flex: 1 }}>{label}</AppText>
    </Pressable>
  );
}
