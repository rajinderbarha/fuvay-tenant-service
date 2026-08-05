import React from "react";
import { View } from "react-native";
import { useTheme } from "../../design-system/theme";
import { AppText } from "../AppText";
import { AppButton } from "../AppButton";

export interface AddressFormFooterProps {
  mode: "add" | "edit";
  canSave: boolean;
  saving: boolean;
  onSave: () => void;
}

/** `AppButton`'s own internal busy-guard already prevents a second tap
 * while `onSave` (async) is in flight -- no separate double-submit guard
 * needed here (spec section 8). */
export function AddressFormFooter({ mode, canSave, saving, onSave }: AddressFormFooterProps) {
  const { theme } = useTheme();
  return (
    <View style={{ gap: theme.spacing.sm }}>
      <AppButton
        label={mode === "add" ? "Save address" : "Save changes"}
        onPress={onSave}
        disabled={!canSave}
        loading={saving}
        fullWidth
      />
      <AppText variant="caption" color="tertiary" align="center">You can choose another address while booking.</AppText>
    </View>
  );
}
